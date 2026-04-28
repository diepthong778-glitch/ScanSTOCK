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

    def as_dict(self):
        return {
            "id": self.reference.id if self.reference else None,
            "title": self.reference.title if self.reference else "No reference match",
            "source": self.reference.source if self.reference else "",
            "score": self.similarity_percent,
            "fuzzy_score": self.fuzzy_score,
            "tfidf_score": self.tfidf_score,
            "excerpt": self.excerpt,
        }


def check_plagiarism(input_text: str) -> PlagiarismCheck:
    clean_text = _normalize(input_text)
    references = list(ReferenceDocument.objects.all())

    if not references:
        check = PlagiarismCheck.objects.create(input_text=input_text)
        check.matches = []
        check.risk_level = "low"
        return check

    matches = _rank_matches(clean_text, references)[:3]
    best = matches[0] if matches else MatchResult(None, 0, 0, 0, "")
    check = PlagiarismCheck.objects.create(
        input_text=input_text,
        similarity_percent=best.similarity_percent,
        matched_document=best.reference,
        matched_excerpt=best.excerpt,
        fuzzy_score=best.fuzzy_score,
        tfidf_score=best.tfidf_score,
    )
    check.matches = [match.as_dict() for match in matches]
    check.risk_level = similarity_risk_level(best.similarity_percent)
    return check


def similarity_risk_level(score: float) -> str:
    if score > 60:
        return "high"
    if score > 25:
        return "medium"
    return "low"


def _rank_matches(input_text: str, references: list[ReferenceDocument]) -> list[MatchResult]:
    corpus = [input_text] + [_normalize(reference.content) for reference in references]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)
    vectors = vectorizer.fit_transform(corpus)
    tfidf_scores = cosine_similarity(vectors[0:1], vectors[1:]).flatten()

    matches: list[MatchResult] = []
    for index, reference in enumerate(references):
        reference_text = _normalize(reference.content)
        fuzzy_score = max(
            fuzz.token_set_ratio(input_text, reference_text),
            fuzz.partial_ratio(input_text, reference_text),
        )
        tfidf_score = float(tfidf_scores[index] * 100)
        similarity = round((0.42 * fuzzy_score) + (0.58 * tfidf_score), 2)
        excerpt = _matched_excerpt(input_text, reference.content)
        matches.append(
            MatchResult(
                reference=reference,
                similarity_percent=similarity,
                fuzzy_score=round(float(fuzzy_score), 2),
                tfidf_score=round(tfidf_score, 2),
                excerpt=excerpt,
            )
        )

    return sorted(matches, key=lambda match: match.similarity_percent, reverse=True)


def _matched_excerpt(input_text: str, reference_text: str, window_words: int = 55) -> str:
    input_words = _normalize(input_text).split()
    reference_words = reference_text.split()
    if not reference_words:
        return ""

    probes = [
        " ".join(input_words[: min(35, len(input_words))]),
        " ".join(input_words[max(0, len(input_words) // 2 - 15) : len(input_words) // 2 + 20]),
    ]
    best_start = 0
    best_score = -1.0

    for start in range(0, len(reference_words), max(1, window_words // 3)):
        window = " ".join(reference_words[start : start + window_words])
        score = max(fuzz.partial_ratio(probe, window) for probe in probes if probe)
        if score > best_score:
            best_score = score
            best_start = start

    return " ".join(reference_words[best_start : best_start + window_words])


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(ascii_text.strip().lower().split())
