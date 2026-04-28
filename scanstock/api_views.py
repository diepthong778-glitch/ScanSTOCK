from rest_framework.views import APIView

from services.ocr_service import is_tesseract_available
from utils.response_utils import success_response


class HealthAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return success_response(
            {
                "status": "ok",
                "tesseractAvailable": is_tesseract_available(),
            }
        )
