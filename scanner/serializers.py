from rest_framework import serializers

from scanner.models import ScanJob


class ScanJobCreateSerializer(serializers.Serializer):
    image = serializers.ImageField(write_only=True)
    mode = serializers.ChoiceField(
        choices=["bw", "gray", "color", "ocr"],
        default="bw",
        required=False,
    )
    lang = serializers.ChoiceField(
        choices=["eng", "vie", "eng+vie"],
        default="eng+vie",
        required=False,
    )


class ScanJobSerializer(serializers.ModelSerializer):
    original_image_url = serializers.SerializerMethodField()
    scanned_image_url = serializers.SerializerMethodField()
    pdf_file_url = serializers.SerializerMethodField()

    class Meta:
        model = ScanJob
        fields = [
            "id",
            "status",
            "original_image_url",
            "scanned_image_url",
            "pdf_file_url",
            "ocr_text",
            "document_type",
            "document_confidence",
            "classification_info",
            "fake_risk_score",
            "fake_risk_level",
            "fake_reasons",
            "quality_info",
            "boundary_info",
            "ocr_info",
            "manual_review_recommended",
            "error_message",
            "created_at",
            "updated_at",
        ]

    def get_original_image_url(self, obj):
        return self._absolute_file_url(obj.original_image)

    def get_scanned_image_url(self, obj):
        return self._absolute_file_url(obj.scanned_image)

    def get_pdf_file_url(self, obj):
        return self._absolute_file_url(obj.pdf_file)

    def _absolute_file_url(self, file_field):
        if not file_field:
            return None
        request = self.context.get("request")
        url = file_field.url
        return request.build_absolute_uri(url) if request else url
