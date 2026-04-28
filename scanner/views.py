from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from scanner.models import ScanJob
from scanner.serializers import ScanJobCreateSerializer, ScanJobSerializer
from scanner.services import process_scan_job


class ScanDocumentAPIView(APIView):
    def post(self, request):
        serializer = ScanJobCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job = ScanJob.objects.create(original_image=serializer.validated_data["image"])
        try:
            process_scan_job(
                job,
                mode=serializer.validated_data.get("mode", "bw"),
                lang=serializer.validated_data.get("lang", "eng+vie"),
            )
        except Exception:
            job.refresh_from_db()
            data = ScanJobSerializer(job, context={"request": request}).data
            return Response(data, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        data = ScanJobSerializer(job, context={"request": request}).data
        return Response(data, status=status.HTTP_201_CREATED)
