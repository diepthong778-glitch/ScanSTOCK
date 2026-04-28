from __future__ import annotations

import os
import sys
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "scanstock.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402


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
    dataset_path = Path(settings.DATASETS_DIR) / "document_training.csv"
    output_path = Path(settings.AI_MODEL_DIR) / "document_classifier.joblib"

    if not dataset_path.exists():
        raise FileNotFoundError(f"Training dataset not found: {dataset_path}")

    df = pd.read_csv(dataset_path)
    missing_columns = REQUIRED_COLUMNS - set(df.columns)
    if missing_columns:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_columns)}")

    df = df.dropna(subset=["text", "label"])
    df["text"] = df["text"].astype(str).str.strip()
    df["label"] = df["label"].astype(str).str.strip()
    df = df[(df["text"] != "") & (df["label"] != "")]

    unknown_labels = sorted(set(df["label"]) - ALLOWED_LABELS)
    if unknown_labels:
        raise ValueError(f"Unsupported labels: {unknown_labels}. Allowed labels: {sorted(ALLOWED_LABELS)}")

    if df["label"].nunique() < 2:
        raise ValueError("Training requires at least two different labels.")

    pipeline = Pipeline(
        steps=[
            ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=20000)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipeline.fit(df["text"], df["label"])

    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, output_path)
    return output_path


if __name__ == "__main__":
    model_file = train()
    print(f"Saved document classifier to {model_file}")
