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
    risk_level = serializers.SerializerMethodField()
    matches = serializers.SerializerMethodField()

    class Meta:
        model = PlagiarismCheck
        fields = [
            "id",
            "similarity_percent",
            "risk_level",
            "matched_document",
            "matched_excerpt",
            "matches",
            "fuzzy_score",
            "tfidf_score",
            "created_at",
        ]

    def get_risk_level(self, obj):
        if hasattr(obj, "risk_level"):
            return obj.risk_level
        if obj.similarity_percent > 60:
            return "high"
        if obj.similarity_percent > 25:
            return "medium"
        return "low"

    def get_matches(self, obj):
        if hasattr(obj, "matches"):
            return obj.matches
        if not obj.matched_document:
            return []
        return [
            {
                "id": obj.matched_document_id,
                "title": obj.matched_document.title,
                "source": obj.matched_document.source,
                "score": obj.similarity_percent,
                "fuzzy_score": obj.fuzzy_score,
                "tfidf_score": obj.tfidf_score,
                "excerpt": obj.matched_excerpt,
            }
        ]
