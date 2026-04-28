from rest_framework import serializers

from plagiarism.models import PlagiarismCheck, ReferenceDocument


class PlagiarismCheckCreateSerializer(serializers.Serializer):
    text = serializers.CharField(write_only=True, allow_blank=False, trim_whitespace=True)

    def validate_text(self, value):
        if len(value.split()) < 3:
            raise serializers.ValidationError("Text must contain at least 3 words.")
        return value


class ReferenceDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferenceDocument
        fields = ["id", "title", "source"]


class PlagiarismCheckSerializer(serializers.ModelSerializer):
    matched_document = ReferenceDocumentSerializer(read_only=True)

    class Meta:
        model = PlagiarismCheck
        fields = [
            "id",
            "similarity_percent",
            "matched_document",
            "matched_excerpt",
            "fuzzy_score",
            "tfidf_score",
            "created_at",
        ]
