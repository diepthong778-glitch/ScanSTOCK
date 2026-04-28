from __future__ import annotations

from typing import Any
import unicodedata


EXPECTED_FIELDS = {
    "cccd_id_card": ["ngay sinh", "quoc tich", "noi thuong tru", "so dinh danh"],
    "invoice": ["tong tien", "ma so thue", "vat", "hoa don"],
    "contract": ["ben a", "ben b", "dieu khoan", "chu ky"],
    "resume": ["experience", "education", "skills"],
    "medical_document": ["chan doan", "bac si", "don thuoc", "benh vien"],
    "bank_statement": ["account", "transaction", "balance"],
    "school_document": ["student", "grade", "school"],
    "receipt": ["total", "paid", "receipt"],
}


def assess_fake_document_risk(
    *,
    ocr_text: str,
    document_type: str,
    quality_info: dict[str, Any],
    boundary_info: dict[str, Any],
    ocr_info: dict[str, Any],
    classification_info: dict[str, Any],
) -> dict[str, Any]:
    score = 0.0
    reasons: list[str] = []

    text = _normalize_text(ocr_text)
    quality_score = float(quality_info.get("quality_score", 0.0))
    boundary_confidence = float(boundary_info.get("boundary_confidence", 0.0))
    ocr_confidence = float(ocr_info.get("ocr_confidence", 0.0))
    classification_confidence = float(classification_info.get("confidence", 0.0))

    if quality_score < 0.45:
        score += 0.18
        reasons.append("Image quality is poor; manual review is recommended.")
    elif quality_score < 0.65:
        score += 0.08
        reasons.append("Image quality is fair and may reduce OCR reliability.")

    if quality_info.get("blur_score", 0) < 80:
        score += 0.14
        reasons.append("Image appears blurry.")

    if quality_info.get("resolution_score", 0) < 0.5:
        score += 0.12
        reasons.append("Image resolution is low for reliable verification.")

    if quality_info.get("compression_warning"):
        score += 0.08
        reasons.append("Image appears heavily compressed.")

    if quality_info.get("shadow_warning"):
        score += 0.08
        reasons.append("Uneven lighting or shadow was detected.")

    if boundary_confidence < 0.45:
        score += 0.14
        reasons.append("Paper boundary confidence is low.")

    if ocr_confidence < 0.45:
        score += 0.16
        reasons.append("OCR confidence is low.")

    if len(text) < 40:
        score += 0.12
        reasons.append("OCR extracted very little readable text.")

    if classification_confidence < 0.55 or document_type == "unknown":
        score += 0.12
        reasons.append("Document type confidence is low.")

    expected = EXPECTED_FIELDS.get(document_type, [])
    if expected:
        missing = [field for field in expected if field not in text]
        if len(missing) >= max(1, len(expected) - 1):
            score += 0.12
            reasons.append("Several expected fields for this document type were not found.")

    suspicious_terms = ["copy", "sample", "specimen", "void", "fake", "for test"]
    if any(term in text for term in suspicious_terms):
        score += 0.18
        reasons.append("OCR found wording commonly used on samples or non-final documents.")

    score = round(min(score, 0.95), 2)
    if score >= 0.60:
        level = "high"
    elif score >= 0.30:
        level = "medium"
    else:
        level = "low"

    if not reasons:
        reasons.append("No strong suspicious indicators were detected.")

    if score >= 0.30:
        reasons.append("Manual review is recommended for important documents.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "disclaimer": "This is AI-assisted risk analysis, not legal verification.",
    }


def _normalize_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(ascii_text.lower().split())
