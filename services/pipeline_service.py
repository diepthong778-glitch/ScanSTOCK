from __future__ import annotations

from services.classification_service import classify_document
from services.extraction_service import extract_fields
from services.image_service import (
    decode_image,
    detect_document_contour,
    enhance_for_ocr,
    estimate_quality,
    four_point_transform,
)
from services.ocr_service import clean_text, run_ocr
from services.tamper_service import analyze_tamper_warnings


def process_document_image(image_bytes: bytes, lang: str = "eng") -> dict:
    warnings: list[str] = []
    processing_steps: list[str] = []

    try:
        image = decode_image(image_bytes)
        processing_steps.append("image_loaded")
    except ValueError as exc:
        return failure_response(str(exc), processing_steps)

    contour = detect_document_contour(image)
    boundary_found = contour is not None
    if boundary_found:
        processing_steps.append("document_detected")
    else:
        warnings.append("document_boundary_not_found")
        processing_steps.append("document_contour_not_found_using_original")

    try:
        scanned_image = four_point_transform(image, contour) if boundary_found else image
        processing_steps.append("perspective_corrected" if boundary_found else "perspective_skipped")
    except Exception:
        scanned_image = image
        boundary_found = False
        warnings.append("document_boundary_not_found")
        processing_steps.append("crop_failed_using_original")

    try:
        ocr_image = enhance_for_ocr(scanned_image)
        processing_steps.append("image_enhanced_for_ocr")
    except Exception as exc:
        return failure_response(f"image_enhancement_failed: {exc}", processing_steps, warnings)

    ocr_result = run_ocr(ocr_image, lang)
    if not ocr_result["success"]:
        warnings.append("ocr_failed")
        quality = estimate_quality(scanned_image, "", boundary_found)
        warnings.extend(unique_new(quality["warnings"], warnings))
        return {
            "success": False,
            "documentType": "unknown",
            "rawText": "",
            "cleanText": "",
            "structuredData": {},
            "confidence": quality["confidence"],
            "warnings": warnings,
            "processingSteps": processing_steps + ["ocr_failed"],
            "error": ocr_result["error"],
        }

    processing_steps.append("ocr_completed")
    raw_text = ocr_result["rawText"]
    clean = clean_text(raw_text)
    processing_steps.append("text_cleaned")

    classification = classify_document(clean)
    processing_steps.append("document_classified")

    structured = extract_fields(clean, classification["documentType"])
    processing_steps.append("fields_extracted")

    quality = estimate_quality(scanned_image, clean, boundary_found)
    warnings.extend(unique_new(quality["warnings"], warnings))
    tamper_warnings = analyze_tamper_warnings(
        scanned_image,
        clean,
        float(ocr_result.get("confidence", 0.0)),
        boundary_found,
    )
    warnings.extend(unique_new(tamper_warnings, warnings))
    confidence = round((classification["confidence"] * 0.65) + (quality["confidence"] * 0.35), 2)

    return {
        "success": True,
        "documentType": classification["documentType"],
        "rawText": raw_text,
        "cleanText": clean,
        "structuredData": structured,
        "confidence": confidence,
        "warnings": warnings,
        "processingSteps": processing_steps,
        "matchedSignals": classification["matchedSignals"],
        "ocrConfidence": ocr_result.get("confidence", 0.0),
        "quality": {
            "blurScore": quality["blurScore"],
            "contrastScore": quality["contrastScore"],
            "textLength": quality["textLength"],
            "boundaryFound": boundary_found,
        },
    }


def failure_response(error: str, processing_steps: list[str], warnings: list[str] | None = None) -> dict:
    return {
        "success": False,
        "documentType": "unknown",
        "rawText": "",
        "cleanText": "",
        "structuredData": {},
        "confidence": 0.0,
        "warnings": warnings or [],
        "processingSteps": processing_steps,
        "error": error,
    }


def unique_new(items: list[str], existing: list[str]) -> list[str]:
    return [item for item in items if item not in existing]
