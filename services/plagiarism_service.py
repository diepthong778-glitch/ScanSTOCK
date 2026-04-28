from __future__ import annotations

import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def check_text_similarity(text: str, sources: list[str] | None = None) -> dict:
    clean_input = normalize_text(text)
    clean_sources = [normalize_text(source) for source in (sources or []) if normalize_text(source)]
    notes: list[str] = []

    if not clean_input:
        return {
            "success": False,
            "overallScore": 0.0,
            "riskLevel": "low",
            "matches": [],
            "notes": ["Input text is empty."],
        }

    if not clean_sources:
        repetition = internal_repetition_score(clean_input)
        notes.append("External internet plagiarism checking is not available offline.")
        notes.append("No source texts were provided, so only internal repetition analysis was performed.")
        return {
            "success": True,
            "overallScore": repetition,
            "riskLevel": risk_level(repetition),
            "matches": [],
            "notes": notes,
        }

    corpus = [clean_input] + clean_sources
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")
    vectors = vectorizer.fit_transform(corpus)
    scores = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

    matches = []
    for index, score in enumerate(scores):
        score_float = round(float(score), 3)
        matches.append(
            {
                "sourceIndex": index,
                "score": score_float,
                "excerpt": best_excerpt(clean_input, sources[index]),
            }
        )

    matches.sort(key=lambda item: item["score"], reverse=True)
    overall = matches[0]["score"] if matches else 0.0
    notes.append("Compared against provided offline source texts using TF-IDF cosine similarity.")

    return {
        "success": True,
        "overallScore": overall,
        "riskLevel": risk_level(overall),
        "matches": matches[:3],
        "notes": notes,
    }


def internal_repetition_score(text: str) -> float:
    words = re.findall(r"\b[a-zA-Z]{4,}\b", text.lower())
    if not words:
        return 0.0
    unique_ratio = len(set(words)) / len(words)
    return round(max(0.0, min(1.0, 1.0 - unique_ratio)), 3)


def risk_level(score: float) -> str:
    if score >= 0.61:
        return "high"
    if score >= 0.26:
        return "medium"
    return "low"


def best_excerpt(input_text: str, source: str, window_words: int = 45) -> str:
    source_words = source.split()
    input_terms = set(re.findall(r"\b[a-zA-Z]{5,}\b", input_text.lower()))
    if not source_words or not input_terms:
        return source[:240]

    best_start = 0
    best_score = -1
    step = max(1, window_words // 3)
    for start in range(0, len(source_words), step):
        window = source_words[start : start + window_words]
        window_terms = set(re.findall(r"\b[a-zA-Z]{5,}\b", " ".join(window).lower()))
        score = len(input_terms & window_terms)
        if score > best_score:
            best_score = score
            best_start = start
    return " ".join(source_words[best_start : best_start + window_words])


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())
