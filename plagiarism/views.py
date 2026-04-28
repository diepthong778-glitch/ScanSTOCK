from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.plagiarism_service import check_text_similarity
from plagiarism.serializers import (
    PlagiarismCheckCreateSerializer,
    PlagiarismCheckSerializer,
)
from plagiarism.services import check_plagiarism


class PlagiarismCheckAPIView(APIView):
    def post(self, request):
        serializer = PlagiarismCheckCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["text"]
        sources = request.data.get("sources")
        if sources is not None:
            if not isinstance(sources, list) or not all(isinstance(item, str) for item in sources):
                return Response(
                    {
                        "success": False,
                        "message": "Field 'sources' must be a list of text strings.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            result = check_text_similarity(text, sources=sources)
            return Response(result, status=status.HTTP_200_OK)

        offline_result = check_text_similarity(text, sources=None)
        check = check_plagiarism(text)
        data = PlagiarismCheckSerializer(check).data
        data.update(
            {
                "success": True,
                "overallScore": round(data["similarity_percent"] / 100, 3),
                "riskLevel": data["risk_level"],
                "notes": offline_result["notes"],
            }
        )
        return Response(data, status=status.HTTP_201_CREATED)
