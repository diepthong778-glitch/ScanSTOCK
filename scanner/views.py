from pathlib import Path
from django.conf import settings
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status

from .models import ScanJob
from .services import scan_image, run_ocr, export_pdf
from ai_core.classifier import ai_classify
from ai_core.fake_detector import fake_document_risk


@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def scan_document_api(request):
    image = request.FILES.get("image")
    mode = request.data.get("mode", "bw")
    lang = request.data.get("lang", "eng+vie")

    if not image:
        return Response(
            {"error": "Vui lòng upload ảnh."},
            status=status.HTTP_400_BAD_REQUEST
        )

    job = ScanJob.objects.create(original_image=image)

    try:
        original_path = Path(job.original_image.path)

        result_dir = Path(settings.MEDIA_ROOT) / "scanner" / "results"
        pdf_dir = Path(settings.MEDIA_ROOT) / "scanner" / "pdfs"

        result_dir.mkdir(parents=True, exist_ok=True)
        pdf_dir.mkdir(parents=True, exist_ok=True)

        scanned_path = result_dir / f"scan_{job.id}.jpg"
        pdf_path = pdf_dir / f"scan_{job.id}.pdf"

        scan_image(original_path, scanned_path, mode=mode)
        ocr_text = run_ocr(scanned_path, lang=lang)
        export_pdf(scanned_path, pdf_path)

        classification = ai_classify(ocr_text)

        fake_result = fake_document_risk(
            image_path=scanned_path,
            document_type=classification["label"],
            ocr_text=ocr_text
        )

        job.scanned_image.name = f"scanner/results/scan_{job.id}.jpg"
        job.pdf_file.name = f"scanner/pdfs/scan_{job.id}.pdf"
        job.ocr_text = ocr_text
        job.document_type = classification["label"]
        job.document_confidence = classification["confidence"]
        job.fake_risk_score = fake_result["risk_score"]
        job.fake_risk_level = fake_result["risk_level"]
        job.fake_reasons = fake_result["reasons"]
        job.status = "done"
        job.save()

        scanned_image_url = request.build_absolute_uri(job.scanned_image.url)
        pdf_file_url = request.build_absolute_uri(job.pdf_file.url)

        return Response({
            "message": "Scan thành công.",
            "id": job.id,
            "job_id": job.id,
            "scanned_image": scanned_image_url,
            "scanned_image_url": scanned_image_url,
            "pdf_file": pdf_file_url,
            "pdf_file_url": pdf_file_url,
            "ocr_text": ocr_text,
            "document_type": job.document_type,
            "document_confidence": job.document_confidence,
            "fake_risk_score": job.fake_risk_score,
            "fake_risk_level": job.fake_risk_level,
            "fake_reasons": job.fake_reasons,
        }, status=status.HTTP_201_CREATED)

    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)
        job.save()

        return Response(
            {"error": str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
