from __future__ import annotations

from io import BytesIO

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError


def decode_image(image_bytes: bytes) -> np.ndarray:
    if not image_bytes:
        raise ValueError("empty_image")

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            rgb = np.array(image)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("invalid_or_corrupted_image") from exc

    if rgb.size == 0:
        raise ValueError("invalid_image")

    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def detect_document_contour(image: np.ndarray) -> np.ndarray | None:
    ratio = image.shape[0] / 700.0
    resized = cv2.resize(image, (int(image.shape[1] / ratio), 700))
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    image_area = resized.shape[0] * resized.shape[1]

    for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        area = cv2.contourArea(approx)
        if len(approx) == 4 and cv2.isContourConvex(approx) and area > image_area * 0.18:
            return (approx.reshape(4, 2) * ratio).astype("float32")

    return None


def four_point_transform(image: np.ndarray, points: np.ndarray) -> np.ndarray:
    rect = order_points(points)
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


def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.fastNlMeansDenoising(gray, h=10)
    sharpened = sharpen(denoised)
    return cv2.adaptiveThreshold(
        sharpened,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        12,
    )


def estimate_quality(image: np.ndarray, text: str, boundary_found: bool) -> dict:
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast_score = float(np.std(gray))
    text_length = len((text or "").strip())
    warnings: list[str] = []

    if blur_score < 80:
        warnings.append("image_blurry")
    if text_length < 30:
        warnings.append("low_text_detected")
    if contrast_score < 28:
        warnings.append("low_contrast")
    if not boundary_found:
        warnings.append("document_boundary_not_found")

    blur_component = min(1.0, blur_score / 220)
    contrast_component = min(1.0, contrast_score / 70)
    text_component = min(1.0, text_length / 300)
    boundary_component = 1.0 if boundary_found else 0.55
    confidence = round(
        (blur_component * 0.25)
        + (contrast_component * 0.25)
        + (text_component * 0.35)
        + (boundary_component * 0.15),
        2,
    )

    return {
        "blurScore": round(blur_score, 2),
        "contrastScore": round(contrast_score, 2),
        "textLength": text_length,
        "confidence": confidence,
        "warnings": warnings,
    }


def order_points(points: np.ndarray) -> np.ndarray:
    rect = np.zeros((4, 2), dtype="float32")
    sums = points.sum(axis=1)
    diffs = np.diff(points, axis=1)
    rect[0] = points[np.argmin(sums)]
    rect[2] = points[np.argmax(sums)]
    rect[1] = points[np.argmin(diffs)]
    rect[3] = points[np.argmax(diffs)]
    return rect


def sharpen(gray: np.ndarray) -> np.ndarray:
    blurred = cv2.GaussianBlur(gray, (0, 0), 1.0)
    return cv2.addWeighted(gray, 1.45, blurred, -0.45, 0)
