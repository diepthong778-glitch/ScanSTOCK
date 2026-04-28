from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from plagiarism.models import PlagiarismCheck, ReferenceDocument


@dataclass
class MatchResult:
    reference: ReferenceDocument | None
    similarity_percent: float
    fuzzy_score: float
    tfidf_score: float
    excerpt: str


def check_plagiarism(input_text: str) -> PlagiarismCheck:
    clean_text = _normalize(input_text)
    references = list(ReferenceDocument.objects.all())

    if not references:
        return PlagiarismCheck.objects.create(input_text=input_text)

    match = _best_match(clean_text, references)
    return PlagiarismCheck.objects.create(
        input_text=input_text,
        similarity_percent=match.similarity_percent,
        matched_document=match.reference,
        matched_excerpt=match.excerpt,
        fuzzy_score=match.fuzzy_score,
        tfidf_score=match.tfidf_score,
    )


def _best_match(input_text: str, references: list[ReferenceDocument]) -> MatchResult:
    corpus = [input_text] + [_normalize(reference.content) for reference in references]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    vectors = vectorizer.fit_transform(corpus)
    tfidf_scores = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

    best: MatchResult | None = None
    for index, reference in enumerate(references):
        reference_text = _normalize(reference.content)
        fuzzy_score = fuzz.token_set_ratio(input_text, reference_text)
        tfidf_score = float(tfidf_scores[index] * 100)
        similarity = round((0.45 * fuzzy_score) + (0.55 * tfidf_score), 2)
        excerpt = _matched_excerpt(input_text, reference.content)

        result = MatchResult(
            reference=reference,
            similarity_percent=similarity,
            fuzzy_score=round(float(fuzzy_score), 2),
            tfidf_score=round(tfidf_score, 2),
            excerpt=excerpt,
        )
        if best is None or result.similarity_percent > best.similarity_percent:
            best = result

    return best or MatchResult(None, 0, 0, 0, "")


def _matched_excerpt(input_text: str, reference_text: str, window_words: int = 55) -> str:
    input_words = _normalize(input_text).split()
    reference_words = reference_text.split()
    if not reference_words:
        return ""

    probe = " ".join(input_words[: min(35, len(input_words))])
    best_start = 0
    best_score = -1.0

    # Slide by sentence-sized windows to return a useful human review snippet.
    for start in range(0, len(reference_words), max(1, window_words // 3)):
        window = " ".join(reference_words[start : start + window_words])
        score = fuzz.partial_ratio(probe, window)
        if score > best_score:
            best_score = score
            best_start = start

    return " ".join(reference_words[best_start : best_start + window_words])


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(ascii_text.strip().lower().split())
