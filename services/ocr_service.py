from __future__ import annotations

from pathlib import Path
import re

import cv2
import numpy as np
import pytesseract
from PIL import Image
from pytesseract import TesseractError, TesseractNotFoundError


DEFAULT_TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def run_ocr(image, lang: str = "eng") -> dict:
    configure_tesseract()
    pil_image = to_pil_image(image)

    try:
        language = safe_lang(lang)
        raw_text = pytesseract.image_to_string(pil_image, lang=language, config="--psm 6")
        confidence = estimate_ocr_confidence(pil_image, language)
    except TesseractNotFoundError:
        return {
            "success": False,
            "error": "Tesseract OCR is not installed or TESSERACT_CMD is incorrect.",
            "rawText": "",
        }
    except TesseractError as exc:
        return {
            "success": False,
            "error": f"OCR failed: {exc}",
            "rawText": "",
        }

    return {
        "success": True,
        "error": "",
        "rawText": raw_text,
        "confidence": confidence,
        "language": language,
    }


def clean_text(text: str) -> str:
    lines = []
    for line in (text or "").splitlines():
        cleaned = re.sub(r"[ \t]+", " ", line).strip()
        if cleaned:
            lines.append(cleaned)
    return "\n".join(lines)


def configure_tesseract() -> None:
    current = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
    if current and current != "tesseract":
        return
    default_path = Path(DEFAULT_TESSERACT_CMD)
    if default_path.exists():
        pytesseract.pytesseract.tesseract_cmd = str(default_path)


def to_pil_image(image) -> Image.Image:
    if len(image.shape) == 2:
        return Image.fromarray(image)
    rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return Image.fromarray(rgb)


def safe_lang(lang: str) -> str:
    return lang if lang in {"eng", "vie", "eng+vie"} else "eng"


def estimate_ocr_confidence(image: Image.Image, lang: str) -> float:
    try:
        data = pytesseract.image_to_data(image, lang=lang, config="--psm 6", output_type=pytesseract.Output.DICT)
    except Exception:
        return 0.0

    values = []
    for raw in data.get("conf", []):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if value >= 0:
            values.append(value)
    return round(float(np.mean(values)) / 100, 2) if values else 0.0


def is_tesseract_available() -> bool:
    configure_tesseract()
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
