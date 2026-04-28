from dataclasses import dataclass
from pathlib import Path
import unicodedata

import joblib
from django.conf import settings


DOCUMENT_LABELS = {
    "cccd_id_card": "CCCD / ID Card",
    "invoice": "Invoice",
    "contract": "Contract",
    "resume": "CV / Resume",
    "medical_document": "Medical Document",
    "bank_statement": "Bank Statement",
    "school_document": "School Document",
    "receipt": "Receipt",
    "unknown": "Unknown / Needs review",
}

RULES = {
    "cccd_id_card": [
        "can cuoc cong dan",
        "cccd",
        "citizen identity",
        "identity card",
        "so dinh danh",
        "ngay sinh",
        "quoc tich",
        "noi thuong tru",
        "place of residence",
    ],
    "invoice": [
        "invoice",
        "hoa don",
        "vat",
        "tax code",
        "taxcode",
        "ma so thue",
        "tong tien",
        "thanh tien",
        "total amount",
        "totalamount",
        "unit price",
        "subtotal",
    ],
    "contract": [
        "contract",
        "agreement",
        "hop dong",
        "ben a",
        "ben b",
        "terms",
        "dieu khoan",
        "cam ket",
        "effective date",
        "signature",
    ],
    "resume": [
        "curriculum vitae",
        "resume",
        "cv",
        "kinh nghiem",
        "experience",
        "education",
        "skills",
        "work history",
        "projects",
    ],
    "medical_document": [
        "medical",
        "hospital",
        "benh vien",
        "phong kham",
        "diagnosis",
        "chan doan",
        "doctor",
        "bac si",
        "prescription",
        "don thuoc",
    ],
    "bank_statement": [
        "bank statement",
        "account number",
        "transaction",
        "balance",
        "debit",
        "credit",
        "sao ke",
        "ngan hang",
        "so tai khoan",
    ],
    "school_document": [
        "school",
        "university",
        "student",
        "grade",
        "transcript",
        "certificate",
        "truong",
        "sinh vien",
        "bang diem",
    ],
    "receipt": [
        "receipt",
        "bien lai",
        "paid",
        "payment",
        "cashier",
        "change",
        "total",
        "store",
    ],
}


@dataclass(frozen=True)
class ClassificationResult:
    document_type: str
    document_label: str
    confidence: float
    method: str
    matched_signals: list[str]

    def as_dict(self):
        return {
            "document_type": self.document_type,
            "document_label": self.document_label,
            "confidence": self.confidence,
            "method": self.method,
            "matched_signals": self.matched_signals,
        }


def model_path() -> Path:
    return Path(settings.AI_MODEL_DIR) / "document_classifier.joblib"


def classify_document(text: str) -> ClassificationResult:
    rule_result = rule_based_classify(text)
    path = model_path()

    if not path.exists() or not (text or "").strip():
        return _fallback_if_low(rule_result)

    try:
        pipeline = joblib.load(path)
        predicted_label = str(pipeline.predict([text])[0])
        if hasattr(pipeline, "predict_proba"):
            probabilities = pipeline.predict_proba([text])[0]
            confidence = float(max(probabilities))
        else:
            confidence = 0.72
    except Exception:
        return _fallback_if_low(rule_result)

    if predicted_label not in DOCUMENT_LABELS:
        predicted_label = "unknown"

    signals = rule_result.matched_signals if predicted_label == rule_result.document_type else []
    ai_result = ClassificationResult(
        document_type=predicted_label,
        document_label=DOCUMENT_LABELS[predicted_label],
        confidence=round(min(confidence, 0.98), 2),
        method="ai_model",
        matched_signals=signals,
    )

    if ai_result.confidence < 0.55:
        # A weak model prediction should not override a stronger explainable rule match.
        if rule_result.confidence >= 0.55:
            return rule_result
        return ClassificationResult("unknown", DOCUMENT_LABELS["unknown"], ai_result.confidence, "fallback", signals)
    return ai_result


def rule_based_classify(text: str) -> ClassificationResult:
    normalized = _normalize(text)
    best_label = "unknown"
    best_score = 0.0
    best_signals: list[str] = []

    for label, keywords in RULES.items():
        signals = [keyword for keyword in keywords if keyword in normalized]
        score = len(signals) / len(keywords)
        if score > best_score:
            best_score = score
            best_label = label
            best_signals = signals

    if best_score == 0:
        return ClassificationResult("unknown", DOCUMENT_LABELS["unknown"], 0.2, "fallback", [])

    confidence = round(min(0.95, 0.35 + (best_score * 1.45)), 2)
    result = ClassificationResult(
        best_label,
        DOCUMENT_LABELS[best_label],
        confidence,
        "rule",
        best_signals,
    )
    return _fallback_if_low(result)


def _fallback_if_low(result: ClassificationResult) -> ClassificationResult:
    if result.confidence >= 0.55:
        return result
    return ClassificationResult(
        "unknown",
        DOCUMENT_LABELS["unknown"],
        result.confidence,
        "fallback",
        result.matched_signals,
    )


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(ascii_text.lower().split())
