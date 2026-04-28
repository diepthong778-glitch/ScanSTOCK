from dataclasses import dataclass
from pathlib import Path
import unicodedata

import joblib
from django.conf import settings


DOCUMENT_LABELS = {
    "cccd_id_card": "CCCD / ID card",
    "invoice": "Invoice",
    "contract": "Contract",
    "resume": "CV / Resume",
    "medical_document": "Medical document",
    "unknown": "Unknown",
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
    ],
    "invoice": [
        "invoice",
        "hoa don",
        "vat",
        "tax code",
        "ma so thue",
        "tong tien",
        "thanh tien",
        "unit price",
    ],
    "contract": [
        "contract",
        "hop dong",
        "ben a",
        "ben b",
        "terms",
        "dieu khoan",
        "cam ket",
        "effective date",
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
}


@dataclass(frozen=True)
class ClassificationResult:
    document_type: str
    document_label: str
    confidence: float
    method: str

    def as_dict(self):
        return {
            "document_type": self.document_type,
            "document_label": self.document_label,
            "confidence": self.confidence,
            "method": self.method,
        }


def model_path() -> Path:
    return Path(settings.AI_MODEL_DIR) / "document_classifier.joblib"


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(ascii_text.lower().split())


def rule_based_classify(text: str) -> ClassificationResult:
    normalized = _normalize(text)
    best_label = "unknown"
    best_score = 0.0

    for label, keywords in RULES.items():
        matched = sum(1 for keyword in keywords if keyword in normalized)
        score = matched / len(keywords)
        if score > best_score:
            best_score = score
            best_label = label

    if best_score == 0:
        return ClassificationResult("unknown", DOCUMENT_LABELS["unknown"], 0.2, "rule")

    confidence = round(min(0.95, 0.45 + best_score), 2)
    return ClassificationResult(best_label, DOCUMENT_LABELS[best_label], confidence, "rule")


def classify_document(text: str) -> ClassificationResult:
    path = model_path()
    if not path.exists() or not (text or "").strip():
        return rule_based_classify(text)

    pipeline = joblib.load(path)
    predicted_label = str(pipeline.predict([text])[0])

    if hasattr(pipeline, "predict_proba"):
        probabilities = pipeline.predict_proba([text])[0]
        confidence = float(max(probabilities))
    else:
        confidence = 0.75

    if predicted_label not in DOCUMENT_LABELS:
        predicted_label = "unknown"

    return ClassificationResult(
        document_type=predicted_label,
        document_label=DOCUMENT_LABELS[predicted_label],
        confidence=round(min(confidence, 0.98), 2),
        method="ai_model",
    )
