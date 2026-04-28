from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from plagiarism.serializers import (
    PlagiarismCheckCreateSerializer,
    PlagiarismCheckSerializer,
)
from plagiarism.services import check_plagiarism


class PlagiarismCheckAPIView(APIView):
    def post(self, request):
        serializer = PlagiarismCheckCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        check = check_plagiarism(serializer.validated_data["text"])
        data = PlagiarismCheckSerializer(check).data
        return Response(data, status=status.HTTP_201_CREATED)
