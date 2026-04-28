from __future__ import annotations

from typing import Any
import unicodedata

import cv2
import numpy as np


EXPECTED_FIELDS = {
    "cccd_id_card": ["ngay sinh", "quoc tich", "noi thuong tru"],
    "invoice": ["tong tien", "ma so thue", "vat"],
    "contract": ["ben a", "ben b", "dieu khoan"],
    "resume": ["experience", "education", "skills"],
    "medical_document": ["chan doan", "bac si", "don thuoc"],
}


def assess_fake_document_risk(
    original_image: np.ndarray,
    scanned_image: np.ndarray,
    ocr_text: str,
    document_type: str,
    boundary_found: bool,
) -> dict[str, Any]:
    score = 0.0
    reasons: list[str] = []

    text = _normalize_text(ocr_text)
    gray = cv2.cvtColor(scanned_image, cv2.COLOR_BGR2GRAY)
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    if not boundary_found:
        score += 18
        reasons.append("Document boundary was not confidently detected.")

    if blur_score < 80:
        score += 18
        reasons.append("Scanned output is blurry, which reduces verification confidence.")

    if brightness < 45 or brightness > 225:
        score += 12
        reasons.append("Image brightness is outside a normal scan range.")

    if contrast < 25:
        score += 12
        reasons.append("Image has unusually low contrast.")

    if len(text) < 40:
        score += 18
        reasons.append("OCR extracted very little readable text.")

    expected = EXPECTED_FIELDS.get(document_type, [])
    if expected:
        missing = [field for field in expected if field not in text]
        if len(missing) >= max(1, len(expected) - 1):
            score += 14
            reasons.append("Several expected fields for this document type were not found.")

    suspicious_terms = ["copy", "sample", "specimen", "void", "fake", "for test"]
    if any(term in text for term in suspicious_terms):
        score += 20
        reasons.append("OCR found wording commonly used on samples or non-final documents.")

    # This is a risk heuristic, not a forensic conclusion. Keep it below certainty.
    score = round(min(score, 95.0), 2)
    if score >= 60:
        level = "high"
    elif score >= 30:
        level = "medium"
    else:
        level = "low"

    if not reasons:
        reasons.append("No strong visual or OCR risk indicators were detected.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "disclaimer": "Risk is heuristic and does not prove a document is fake.",
    }


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(ascii_text.lower().split())
