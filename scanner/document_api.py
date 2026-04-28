from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.views import APIView

from services.classification_service import classify_document
from services.image_service import decode_image, enhance_for_ocr
from services.ocr_service import clean_text, run_ocr
from services.pipeline_service import process_document_image
from utils.file_utils import validate_uploaded_image
from utils.response_utils import error_response, success_response


class DocumentScanAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file") or request.FILES.get("image")
        valid, message = validate_uploaded_image(uploaded_file)
        if not valid:
            return error_response(message)

        lang = request.query_params.get("lang") or request.data.get("lang") or "eng"
        result = process_document_image(uploaded_file.read(), lang=lang)
        http_status = status.HTTP_200_OK if result.get("success") else status.HTTP_422_UNPROCESSABLE_ENTITY
        return success_response(result, http_status=http_status)


class ExtractTextAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file") or request.FILES.get("image")
        valid, message = validate_uploaded_image(uploaded_file)
        if not valid:
            return error_response(message)

        lang = request.query_params.get("lang") or request.data.get("lang") or "eng"
        try:
            image = decode_image(uploaded_file.read())
            ocr_image = enhance_for_ocr(image)
            ocr_result = run_ocr(ocr_image, lang=lang)
        except Exception as exc:
            return error_response(f"Could not process image: {exc}", status.HTTP_422_UNPROCESSABLE_ENTITY)

        if not ocr_result.get("success"):
            return error_response(
                ocr_result.get("error", "OCR failed."),
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                rawText="",
            )

        raw_text = ocr_result.get("rawText", "")
        return success_response(
            {
                "success": True,
                "rawText": raw_text,
                "cleanText": clean_text(raw_text),
                "ocrConfidence": ocr_result.get("confidence", 0.0),
            }
        )


class ClassifyDocumentAPIView(APIView):
    def post(self, request):
        text = request.data.get("text", "")
        if not isinstance(text, str) or not text.strip():
            return error_response("Field 'text' is required.")
        result = classify_document(text)
        return success_response(result)
