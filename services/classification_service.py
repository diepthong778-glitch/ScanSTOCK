from __future__ import annotations

import re


DOCUMENT_KEYWORDS = {
    "invoice": [
        "invoice",
        "hoa don",
        "tax",
        "vat",
        "total",
        "amount",
        "subtotal",
        "unit price",
        "payment",
    ],
    "cv": [
        "curriculum vitae",
        "resume",
        "experience",
        "education",
        "skills",
        "projects",
        "email",
        "phone",
    ],
    "citizen_id": [
        "citizen",
        "identity",
        "id card",
        "can cuoc",
        "cccd",
        "nationality",
        "date of birth",
        "dob",
    ],
    "contract": [
        "contract",
        "agreement",
        "party",
        "terms",
        "conditions",
        "signature",
        "effective date",
        "ben a",
        "ben b",
    ],
    "certificate": [
        "certificate",
        "certify",
        "awarded",
        "completion",
        "completed",
        "diploma",
        "training",
    ],
}


def classify_document(clean_text: str) -> dict:
    normalized = normalize(clean_text)
    best_type = "unknown"
    best_score = 0.0
    best_signals: list[str] = []

    for document_type, keywords in DOCUMENT_KEYWORDS.items():
        signals = [keyword for keyword in keywords if keyword in normalized]
        score = len(signals) / len(keywords)
        if score > best_score:
            best_type = document_type
            best_score = score
            best_signals = signals

    if best_score == 0:
        return {
            "documentType": "unknown",
            "confidence": 0.2,
            "matchedSignals": [],
        }

    confidence = round(min(0.95, 0.35 + (best_score * 1.35)), 2)
    if confidence < 0.5:
        return {
            "documentType": "unknown",
            "confidence": confidence,
            "matchedSignals": best_signals,
        }

    return {
        "documentType": best_type,
        "confidence": confidence,
        "matchedSignals": best_signals,
    }


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()
