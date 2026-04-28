from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import cv2
import img2pdf
import numpy as np
import pytesseract
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError
from pytesseract import TesseractError, TesseractNotFoundError

from ai_core.classifier import classify_document
from ai_core.fake_detector import assess_fake_document_risk
from scanner.models import ScanJob


MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MIN_IMAGE_EDGE = 420
MAX_PROCESS_EDGE = 2200


@dataclass
class BoundaryCandidate:
    points: np.ndarray
    confidence: float
    strategy: str
    area_ratio: float


@dataclass
class ScanArtifacts:
    scanned_image: np.ndarray
    ocr_image: np.ndarray
    boundary_info: dict
    quality_info: dict


class DocumentScanError(Exception):
    pass


def process_scan_job(job: ScanJob, *, mode: str = "bw", lang: str = "eng+vie") -> ScanJob:
    try:
        original_path = Path(job.original_image.path)
        image = _read_and_validate_image(original_path)
        artifacts = _scan_document(image, mode=mode)
        scanned_jpg = _encode_jpeg(artifacts.scanned_image)
        scanned_pdf = img2pdf.convert(scanned_jpg)

        job.scanned_image.save(f"scan_{job.pk}.jpg", ContentFile(scanned_jpg), save=False)
        job.pdf_file.save(f"scan_{job.pk}.pdf", ContentFile(scanned_pdf), save=False)

        ocr = _extract_ocr(artifacts.ocr_image, requested_lang=lang)
        classification = classify_document(ocr["ocr_text"])
        classification_info = classification.as_dict()
        risk = assess_fake_document_risk(
            ocr_text=ocr["ocr_text"],
            document_type=classification.document_type,
            quality_info=artifacts.quality_info,
            boundary_info=artifacts.boundary_info,
            ocr_info=ocr,
            classification_info=classification_info,
        )

        manual_review = _manual_review_recommended(
            artifacts.quality_info,
            artifacts.boundary_info,
            ocr,
            classification_info,
            risk,
        )

        job.ocr_text = ocr["ocr_text"]
        job.document_type = classification.document_type
        job.document_confidence = classification.confidence
        job.classification_info = classification_info
        job.fake_risk_score = risk["score"]
        job.fake_risk_level = risk["level"]
        job.fake_reasons = risk["reasons"]
        job.quality_info = artifacts.quality_info
        job.boundary_info = artifacts.boundary_info
        job.ocr_info = ocr
        job.manual_review_recommended = manual_review
        job.status = ScanJob.Status.DONE
        job.error_message = ""
        job.save()
        return job
    except Exception as exc:
        job.status = ScanJob.Status.FAILED
        job.error_message = _friendly_error(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise DocumentScanError(job.error_message) from exc


def _read_and_validate_image(path: Path) -> np.ndarray:
    if not path.exists():
        raise DocumentScanError("Uploaded image file was not saved correctly.")

    if path.stat().st_size > MAX_UPLOAD_BYTES:
        raise DocumentScanError("Image is too large. Please upload an image smaller than 12 MB.")

    try:
        with Image.open(path) as pil_image:
            pil_image.verify()
    except (UnidentifiedImageError, OSError):
        raise DocumentScanError("Invalid or corrupted image. Please upload a JPG, PNG, or camera image.")

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise DocumentScanError("Uploaded file could not be read as an image.")

    height, width = image.shape[:2]
    if min(height, width) < MIN_IMAGE_EDGE:
        raise DocumentScanError("Image resolution is too low. Please upload a clearer, larger image.")

    return _resize_for_processing(image)


def _resize_for_processing(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    longest = max(height, width)
    if longest <= MAX_PROCESS_EDGE:
        return image
    scale = MAX_PROCESS_EDGE / longest
    return cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_AREA)


def _scan_document(image: np.ndarray, *, mode: str) -> ScanArtifacts:
    quality_info = _analyze_quality(image)
    candidate = _best_boundary_candidate(image)

    if candidate:
        warped = _four_point_transform(image, candidate.points)
        boundary_info = {
            "paper_detected": True,
            "boundary_confidence": round(float(candidate.confidence), 2),
            "strategy": candidate.strategy,
            "area_ratio": round(float(candidate.area_ratio), 3),
            "manual_correction_ready": bool(candidate.confidence < 0.65),
        }
    else:
        warped = image.copy()
        boundary_info = {
            "paper_detected": False,
            "boundary_confidence": 0.0,
            "strategy": "full_image_fallback",
            "area_ratio": 1.0,
            "manual_correction_ready": True,
        }

    warped = _normalize_orientation(warped)
    deskewed = _deskew(warped)
    scanned_image = _enhance_scan(deskewed, mode=mode)
    ocr_image = _enhance_scan(deskewed, mode="ocr")
    return ScanArtifacts(scanned_image=scanned_image, ocr_image=ocr_image, boundary_info=boundary_info, quality_info=quality_info)


def _analyze_quality(image: np.ndarray) -> dict:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape[:2]
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))
    resolution_score = min(1.0, (width * height) / (1400 * 1000))

    blur_component = min(1.0, blur_score / 220)
    brightness_component = max(0.0, 1.0 - abs(brightness - 145) / 145)
    contrast_component = min(1.0, contrast / 70)
    quality_score = round(
        (blur_component * 0.35)
        + (brightness_component * 0.20)
        + (contrast_component * 0.25)
        + (resolution_score * 0.20),
        2,
    )

    warnings: list[str] = []
    if blur_score < 80:
        warnings.append("Image may be blurry. Hold the camera steady and retake if possible.")
    if brightness < 55:
        warnings.append("Image is too dark. Use better lighting.")
    if brightness > 225:
        warnings.append("Image is overexposed. Avoid glare on paper.")
    if contrast < 28:
        warnings.append("Image contrast is low. Place the paper on a darker background.")
    if resolution_score < 0.5:
        warnings.append("Resolution is low. Upload a higher-resolution photo.")

    shadow_warning = _detect_shadow_warning(gray)
    if shadow_warning:
        warnings.append("Uneven lighting or shadows were detected.")

    compression_warning = _detect_compression_warning(gray)
    if compression_warning:
        warnings.append("Image may be heavily compressed.")

    if quality_score >= 0.85:
        level = "excellent"
    elif quality_score >= 0.68:
        level = "good"
    elif quality_score >= 0.45:
        level = "fair"
    else:
        level = "poor"

    return {
        "quality_score": quality_score,
        "quality_level": level,
        "quality_warnings": warnings,
        "blur_score": round(blur_score, 2),
        "brightness_score": round(brightness_component, 2),
        "contrast_score": round(contrast_component, 2),
        "resolution_score": round(resolution_score, 2),
        "shadow_warning": shadow_warning,
        "compression_warning": compression_warning,
    }


def _detect_shadow_warning(gray: np.ndarray) -> bool:
    resized = cv2.resize(gray, (160, 160), interpolation=cv2.INTER_AREA)
    blocks = [
        resized[:80, :80],
        resized[:80, 80:],
        resized[80:, :80],
        resized[80:, 80:],
    ]
    means = [float(np.mean(block)) for block in blocks]
    return max(means) - min(means) > 55


def _detect_compression_warning(gray: np.ndarray) -> bool:
    edges = cv2.Canny(gray, 90, 180)
    edge_density = float(np.mean(edges > 0))
    return edge_density > 0.22


def _best_boundary_candidate(image: np.ndarray) -> BoundaryCandidate | None:
    candidates: list[BoundaryCandidate] = []
    strategies = [
        ("canny_edges", _edges_canny(image)),
        ("adaptive_threshold", _edges_adaptive_threshold(image)),
        ("morphological_closing", _edges_morphological(image)),
    ]

    for strategy, mask in strategies:
        candidates.extend(_contour_candidates(mask, image.shape[:2], strategy))

    if not candidates:
        return None
    return max(candidates, key=lambda candidate: candidate.confidence)


def _edges_canny(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(gray, 50, 150)
    return cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)


def _edges_adaptive_threshold(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (7, 7), 0)
    thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 35, 9)
    return cv2.bitwise_not(thresh)


def _edges_morphological(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
    closed = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    gradient = cv2.morphologyEx(closed, cv2.MORPH_GRADIENT, kernel)
    _, mask = cv2.threshold(gradient, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return mask


def _contour_candidates(mask: np.ndarray, shape: tuple[int, int], strategy: str) -> list[BoundaryCandidate]:
    height, width = shape
    image_area = float(height * width)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates: list[BoundaryCandidate] = []

    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
        area = float(cv2.contourArea(contour))
        area_ratio = area / image_area
        if area_ratio < 0.16 or area_ratio > 0.98:
            continue

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        if len(approx) != 4 or not cv2.isContourConvex(approx):
            continue

        points = approx.reshape(4, 2).astype("float32")
        confidence = _rectangle_score(points, area_ratio, width, height)
        if confidence >= 0.30:
            candidates.append(BoundaryCandidate(points, confidence, strategy, area_ratio))
    return candidates


def _rectangle_score(points: np.ndarray, area_ratio: float, image_width: int, image_height: int) -> float:
    rect = _order_points(points)
    top_left, top_right, bottom_right, bottom_left = rect
    widths = [np.linalg.norm(top_right - top_left), np.linalg.norm(bottom_right - bottom_left)]
    heights = [np.linalg.norm(bottom_left - top_left), np.linalg.norm(bottom_right - top_right)]
    if min(widths + heights) <= 1:
        return 0.0

    parallel_score = 1.0 - min(1.0, (abs(widths[0] - widths[1]) / max(widths)) + (abs(heights[0] - heights[1]) / max(heights)))
    aspect = max(widths) / max(heights)
    normalized_aspect = aspect if aspect >= 1 else 1 / aspect
    aspect_score = 1.0 if normalized_aspect <= 2.3 else max(0.0, 1.0 - ((normalized_aspect - 2.3) / 2.0))
    area_score = min(1.0, area_ratio / 0.55)
    margin_score = 0.7 if _touches_image_edge(rect, image_width, image_height) else 1.0
    score = max(0.0, min(1.0, (area_score * 0.45) + (parallel_score * 0.30) + (aspect_score * 0.20) + (margin_score * 0.05)))
    return round(float(score), 2)


def _touches_image_edge(points: np.ndarray, width: int, height: int) -> bool:
    margin = 6
    return bool(
        np.any(points[:, 0] <= margin)
        or np.any(points[:, 1] <= margin)
        or np.any(points[:, 0] >= width - margin)
        or np.any(points[:, 1] >= height - margin)
    )


def _order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1)
    rect[0] = points[np.argmin(sums)]
    rect[2] = points[np.argmax(sums)]
    rect[1] = points[np.argmin(diffs)]
    rect[3] = points[np.argmax(diffs)]
    return rect


def _four_point_transform(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    rect = _order_points(points)
    top_left, top_right, bottom_right, bottom_left = rect
    width_a = np.linalg.norm(bottom_right - bottom_left)
    width_b = np.linalg.norm(top_right - top_left)
    max_width = max(1, int(max(width_a, width_b)))
    height_a = np.linalg.norm(top_right - bottom_right)
    height_b = np.linalg.norm(top_left - bottom_left)
    max_height = max(1, int(max(height_a, height_b)))
    destination = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def _normalize_orientation(image: np.ndarray) -> np.ndarray:
    height, width = image.shape[:2]
    if width > height * 1.35:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return image


def _deskew(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=80, minLineLength=max(60, image.shape[1] // 4), maxLineGap=15)
    if lines is None:
        return image

    angles = []
    for line in lines[:30]:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        if -15 <= angle <= 15:
            angles.append(angle)
    if not angles:
        return image

    angle = float(np.median(angles))
    if abs(angle) < 0.4:
        return image

    height, width = image.shape[:2]
    matrix = cv2.getRotationMatrix2D((width / 2, height / 2), angle, 1.0)
    return cv2.warpAffine(image, matrix, (width, height), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def _enhance_scan(image: np.ndarray, *, mode: str) -> np.ndarray:
    if mode == "color":
        return _enhance_color(image)

    gray = cv2.cvtColor(_reduce_shadow(image), cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)
    sharpened = _sharpen_gray(contrasted)

    if mode == "gray":
        return cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)

    block_size = 31 if mode == "bw" else 25
    threshold = cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        12,
    )
    if mode == "ocr":
        kernel = np.ones((1, 1), np.uint8)
        threshold = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel)
    return cv2.cvtColor(threshold, cv2.COLOR_GRAY2BGR)


def _reduce_shadow(image: np.ndarray) -> np.ndarray:
    rgb_planes = cv2.split(image)
    normalized_planes = []
    for plane in rgb_planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        background = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, background)
        normalized_planes.append(cv2.normalize(diff, None, 0, 255, cv2.NORM_MINMAX))
    return cv2.merge(normalized_planes)


def _enhance_color(image: np.ndarray) -> np.ndarray:
    reduced = _reduce_shadow(image)
    lab = cv2.cvtColor(reduced, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced_l = clahe.apply(l_channel)
    merged = cv2.merge((enhanced_l, a_channel, b_channel))
    enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
    return _sharpen_color(enhanced)


def _sharpen_gray(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
    return cv2.addWeighted(gray, 1.45, blurred, -0.45, 0)


def _sharpen_color(image: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(image, (0, 0), 1.1)
    return cv2.addWeighted(image, 1.35, blurred, -0.35, 0)


def _encode_jpeg(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 94])
    if not ok:
        raise DocumentScanError("Could not encode scanned image.")
    return buffer.tobytes()


def _extract_ocr(image: np.ndarray, *, requested_lang: str) -> dict:
    tesseract_cmd = Path(getattr(settings, "TESSERACT_CMD", ""))
    if tesseract_cmd.exists():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)

    lang = _available_tesseract_lang(requested_lang)
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    try:
        text = pytesseract.image_to_string(pil_image, lang=lang, config="--psm 6")
        data = pytesseract.image_to_data(pil_image, lang=lang, config="--psm 6", output_type=pytesseract.Output.DICT)
    except TesseractNotFoundError as exc:
        raise DocumentScanError("Tesseract OCR is not installed or TESSERACT_CMD is incorrect.") from exc
    except TesseractError as exc:
        raise DocumentScanError(f"OCR failed: {exc}") from exc

    confidences = []
    for value in data.get("conf", []):
        try:
            conf = float(value)
        except (TypeError, ValueError):
            continue
        if conf >= 0:
            confidences.append(conf)

    confidence = round((float(np.mean(confidences)) / 100) if confidences else 0.0, 2)
    return {
        "ocr_text": _clean_ocr_text(text),
        "ocr_confidence": confidence,
        "ocr_language": lang,
    }


def _available_tesseract_lang(requested_lang: str) -> str:
    requested = requested_lang if requested_lang in {"eng", "vie", "eng+vie"} else "eng+vie"
    try:
        available = set(pytesseract.get_languages(config=""))
    except TesseractNotFoundError as exc:
        raise DocumentScanError("Tesseract OCR is not installed or TESSERACT_CMD is incorrect.") from exc

    if requested == "eng+vie" and {"eng", "vie"}.issubset(available):
        return "eng+vie"
    if requested in available:
        return requested
    if "eng" in available:
        return "eng"
    if available:
        return sorted(available)[0]
    raise DocumentScanError("No Tesseract OCR languages are available.")


def _clean_ocr_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in (text or "").splitlines()]
    return "\n".join(line for line in lines if line)


def _manual_review_recommended(
    quality_info: dict,
    boundary_info: dict,
    ocr_info: dict,
    classification_info: dict,
    risk: dict,
) -> bool:
    return any(
        [
            quality_info.get("quality_score", 0) < 0.55,
            boundary_info.get("boundary_confidence", 0) < 0.55,
            ocr_info.get("ocr_confidence", 0) < 0.55,
            classification_info.get("confidence", 0) < 0.55,
            risk.get("level") in {"medium", "high"},
        ]
    )


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, DocumentScanError):
        return str(exc)
    message = str(exc)
    if "tesseract" in message.lower():
        return "Tesseract OCR is not installed or TESSERACT_CMD is incorrect."
    return message or "Server error while scanning the document."
