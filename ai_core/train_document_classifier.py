from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "datasets" / "document_training.csv"
MODEL_DIR = BASE_DIR / "models_ai"
MODEL_PATH = MODEL_DIR / "document_classifier.joblib"

REQUIRED_COLUMNS = {"text", "label"}
ALLOWED_LABELS = {
    "cccd_id_card",
    "invoice",
    "contract",
    "resume",
    "medical_document",
    "bank_statement",
    "school_document",
    "receipt",
    "unknown",
}


def train() -> Path:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f"Training dataset not found: {DATASET_PATH}")

    df = pd.read_csv(DATASET_PATH)
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")

    df = df.dropna(subset=["text", "label"]).copy()
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    df = df[(df["text"] != "") & (df["label"] != "")]

    unknown_labels = sorted(set(df["label"]) - ALLOWED_LABELS)
    if unknown_labels:
        raise ValueError(f"Unsupported labels: {unknown_labels}. Allowed labels: {sorted(ALLOWED_LABELS)}")

    if df["label"].nunique() < 2:
        raise ValueError("Training requires at least two different labels.")

    model = Pipeline(
        [
            ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), min_df=1, max_features=20000)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    model.fit(df["text"], df["label"])

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    return MODEL_PATH


if __name__ == "__main__":
    model_path = train()
    print(f"Saved document classifier to {model_path}")
