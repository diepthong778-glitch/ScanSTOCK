from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .models import ReferenceDocument


def simple_fuzzy_similarity(input_text, reference_text):
    return fuzz.token_set_ratio(input_text, reference_text)


def tfidf_similarity(input_text, reference_text):
    vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([input_text, reference_text])
    score = cosine_similarity(matrix[0:1], matrix[1:2])[0][0]
    return round(score * 100, 2)


def check_plagiarism(input_text):
    references = ReferenceDocument.objects.all()

    best_score = 0
    best_doc = None
    best_excerpt = ""

    for doc in references:
        fuzzy_score = simple_fuzzy_similarity(input_text, doc.content)
        tfidf_score = tfidf_similarity(input_text, doc.content)

        final_score = round((fuzzy_score * 0.4) + (tfidf_score * 0.6), 2)

        if final_score > best_score:
            best_score = final_score
            best_doc = doc
            best_excerpt = doc.content[:500]

    return {
        "similarity_percent": best_score,
        "matched_document": best_doc,
        "matched_excerpt": best_excerpt
    }
