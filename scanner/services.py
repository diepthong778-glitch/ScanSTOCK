from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import img2pdf
import numpy as np
import pytesseract
from django.conf import settings
from django.core.files.base import ContentFile
from PIL import Image

from ai_core.classifier import classify_document
from ai_core.fake_detector import assess_fake_document_risk
from scanner.models import ScanJob


@dataclass
class ScanArtifacts:
    scanned_image: np.ndarray
    boundary_found: bool


class DocumentScanError(Exception):
    pass


def process_scan_job(job: ScanJob) -> ScanJob:
    try:
        original_path = Path(job.original_image.path)
        image = _read_image(original_path)
        artifacts = _scan_document(image)
        scanned_jpg = _encode_jpeg(artifacts.scanned_image)
        scanned_pdf = img2pdf.convert(scanned_jpg)

        scanned_name = f"scan_{job.pk}.jpg"
        pdf_name = f"scan_{job.pk}.pdf"
        job.scanned_image.save(scanned_name, ContentFile(scanned_jpg), save=False)
        job.pdf_file.save(pdf_name, ContentFile(scanned_pdf), save=False)

        ocr_text = _extract_text_from_jpeg(scanned_jpg)
        classification = classify_document(ocr_text)
        risk = assess_fake_document_risk(
            original_image=image,
            scanned_image=artifacts.scanned_image,
            ocr_text=ocr_text,
            document_type=classification.document_type,
            boundary_found=artifacts.boundary_found,
        )

        job.ocr_text = ocr_text
        job.document_type = classification.document_type
        job.document_confidence = classification.confidence
        job.fake_risk_score = risk["score"]
        job.fake_risk_level = risk["level"]
        job.fake_reasons = risk["reasons"]
        job.status = ScanJob.Status.DONE
        job.error_message = ""
        job.save()
        return job
    except Exception as exc:
        job.status = ScanJob.Status.FAILED
        job.error_message = str(exc)
        job.save(update_fields=["status", "error_message", "updated_at"])
        raise


def _read_image(path: Path) -> np.ndarray:
    image = cv2.imread(str(path))
    if image is None:
        raise DocumentScanError("Uploaded file could not be read as an image.")
    return image


def _scan_document(image: np.ndarray) -> ScanArtifacts:
    contour = _find_document_contour(image)
    boundary_found = contour is not None
    warped = _four_point_transform(image, contour.reshape(4, 2)) if boundary_found else image.copy()
    enhanced = _enhance_scan(warped)
    return ScanArtifacts(scanned_image=enhanced, boundary_found=boundary_found)


def _find_document_contour(image: np.ndarray) -> np.ndarray | None:
    ratio = image.shape[0] / 700.0
    resized = cv2.resize(image, (int(image.shape[1] / ratio), 700))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 50, 150)
    edged = cv2.dilate(edged, None, iterations=1)

    contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)[:8]
    image_area = resized.shape[0] * resized.shape[1]

    for contour in contours:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(approx)
        if len(approx) == 4 and area > image_area * 0.18:
            return (approx * ratio).astype("float32")
    return None


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
    max_width = int(max(width_a, width_b))

    height_a = np.linalg.norm(top_right - bottom_right)
    height_b = np.linalg.norm(top_left - bottom_left)
    max_height = int(max(height_a, height_b))

    destination = np.array(
        [[0, 0], [max_width - 1, 0], [max_width - 1, max_height - 1], [0, max_height - 1]],
        dtype="float32",
    )
    matrix = cv2.getPerspectiveTransform(rect, destination)
    return cv2.warpPerspective(image, matrix, (max_width, max_height))


def _enhance_scan(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)
    scanned = cv2.adaptiveThreshold(
        contrasted,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        12,
    )
    return cv2.cvtColor(scanned, cv2.COLOR_GRAY2BGR)


def _encode_jpeg(image: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if not ok:
        raise DocumentScanError("Could not encode scanned image.")
    return buffer.tobytes()


def _extract_text_from_jpeg(jpeg_bytes: bytes) -> str:
    tesseract_cmd = Path(getattr(settings, "TESSERACT_CMD", ""))
    if tesseract_cmd.exists():
        pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)

    image = Image.open(ContentFile(jpeg_bytes))
    lang = _preferred_tesseract_lang()
    return pytesseract.image_to_string(image, lang=lang, config="--psm 6").strip()


def _preferred_tesseract_lang() -> str:
    try:
        languages = set(pytesseract.get_languages(config=""))
    except Exception:
        return "eng"
    if {"eng", "vie"}.issubset(languages):
        return "eng+vie"
    if "vie" in languages:
        return "vie"
    return "eng"
