from __future__ import annotations

import cv2
import numpy as np


def analyze_tamper_warnings(image, clean_text: str, ocr_confidence: float, boundary_found: bool) -> list[str]:
    gray = image if len(image.shape) == 2 else cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    contrast_score = float(np.std(gray))
    warnings: list[str] = []

    if ocr_confidence < 0.35:
        warnings.append("very_low_ocr_confidence")
    if blur_score < 70:
        warnings.append("too_much_blur")
    if len((clean_text or "").strip()) < 25:
        warnings.append("suspiciously_empty_document")
    if contrast_score < 24 or contrast_score > 95:
        warnings.append("abnormal_contrast")
    if not boundary_found:
        warnings.append("document_boundary_not_found")
    if _has_noise_inconsistency(gray):
        warnings.append("possible_tamper_warning")

    return warnings


def _has_noise_inconsistency(gray) -> bool:
    height, width = gray.shape[:2]
    if height < 80 or width < 80:
        return False

    resized = cv2.resize(gray, (240, 240), interpolation=cv2.INTER_AREA)
    blocks = [
        resized[:120, :120],
        resized[:120, 120:],
        resized[120:, :120],
        resized[120:, 120:],
    ]
    noise_levels = [float(np.std(cv2.Laplacian(block, cv2.CV_64F))) for block in blocks]
    return max(noise_levels) - min(noise_levels) > 42
