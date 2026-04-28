from __future__ import annotations

import re


def extract_fields(clean_text: str, document_type: str) -> dict:
    if document_type == "invoice":
        return extract_invoice_fields(clean_text)
    if document_type == "cv":
        return extract_cv_fields(clean_text)
    if document_type == "citizen_id":
        return extract_citizen_id_fields(clean_text)
    if document_type == "contract":
        return extract_contract_fields(clean_text)
    if document_type == "certificate":
        return extract_certificate_fields(clean_text)
    return {}


def extract_invoice_fields(text: str) -> dict:
    return {
        "date": first_item(find_dates(text)),
        "total": first_item(find_total_amounts(text)) or first_item(find_amounts(text)),
        "tax": first_item(find_tax_candidates(text)),
        "vendor": find_vendor_candidate(text),
        "dates": find_dates(text),
        "amountCandidates": find_amounts(text),
    }


def extract_cv_fields(text: str) -> dict:
    skills = []
    skill_words = ["python", "django", "sql", "excel", "javascript", "react", "opencv", "machine learning"]
    lower_text = text.lower()
    for skill in skill_words:
        if skill in lower_text:
            skills.append(skill)

    return {
        "emails": find_emails(text),
        "phones": find_phones(text),
        "skills": skills,
        "educationSignals": [
            signal for signal in ["education", "university", "college", "degree", "hoc van"] if signal in lower_text
        ],
    }


def extract_citizen_id_fields(text: str) -> dict:
    return {
        "idNumber": first_item(re.findall(r"\b\d{9,12}\b", text)),
        "nameCandidate": find_name_candidate(text),
        "dateOfBirth": first_item(find_dates(text)),
        "idNumberCandidates": re.findall(r"\b\d{9,12}\b", text),
        "nationality": first_match(text, r"(nationality|quoc tich)\s*[:\-]?\s*([A-Za-zÀ-ỹ ]{2,40})"),
    }


def extract_contract_fields(text: str) -> dict:
    lower_text = text.lower()
    return {
        "parties": find_parties(text),
        "date": first_item(find_dates(text)),
        "dates": find_dates(text),
        "partySignals": [signal for signal in ["party a", "party b", "ben a", "ben b"] if signal in lower_text],
        "signatureSignal": bool(re.search(r"\b(signature|signed|chu ky|ky ten)\b", lower_text)),
    }


def extract_certificate_fields(text: str) -> dict:
    lower_text = text.lower()
    return {
        "dates": find_dates(text),
        "completionSignals": [
            signal
            for signal in ["certificate", "awarded", "completion", "completed", "diploma", "certify"]
            if signal in lower_text
        ],
    }


def find_dates(text: str) -> list[str]:
    patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",
    ]
    dates: list[str] = []
    for pattern in patterns:
        dates.extend(re.findall(pattern, text))
    return dates


def find_amounts(text: str) -> list[str]:
    matches = re.findall(
        r"(?<![\w/.-])(?:\$|USD|VND)?\s?\d{1,3}(?:[,.]\d{3})*(?:[,.]\d{2})?(?!\s?%)(?![\w/.-])",
        text,
        flags=re.IGNORECASE,
    )
    return [match.strip() for match in matches]


def find_total_amounts(text: str) -> list[str]:
    totals = []
    for line in text.splitlines():
        if re.search(r"\b(total|amount|tong tien|thanh tien)\b", line, flags=re.IGNORECASE):
            totals.extend(find_amounts(line))
    return totals


def find_tax_candidates(text: str) -> list[str]:
    return re.findall(r"\b(?:tax|vat|mst|ma so thue)\s*[:\-]?\s*([A-Z0-9\-]{4,20})", text, flags=re.IGNORECASE)


def find_total_lines(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if re.search(r"\b(total|amount|tong tien|thanh tien)\b", line, flags=re.IGNORECASE)
    ]


def find_emails(text: str) -> list[str]:
    return re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", text)


def find_phones(text: str) -> list[str]:
    return re.findall(r"(?:\+?\d[\d .\-()]{7,}\d)", text)


def first_match(text: str, pattern: str) -> str:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(2).strip() if match else ""


def first_item(values: list[str]) -> str:
    return values[0] if values else ""


def find_vendor_candidate(text: str) -> str:
    for line in text.splitlines()[:6]:
        cleaned = line.strip()
        if len(cleaned) > 3 and not re.search(r"\b(invoice|receipt|date|tax|vat)\b", cleaned, re.IGNORECASE):
            return cleaned
    return ""


def find_name_candidate(text: str) -> str:
    match = re.search(r"\b(name|full name|ho ten)\s*[:\-]?\s*([A-Za-zÀ-ỹ ]{3,60})", text, flags=re.IGNORECASE)
    return match.group(2).strip() if match else ""


def find_parties(text: str) -> list[str]:
    parties = []
    for line in text.splitlines():
        if re.search(r"\b(party|ben a|ben b)\b", line, flags=re.IGNORECASE):
            parties.append(line.strip())
    return parties
