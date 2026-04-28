from django.contrib import admin

from plagiarism.models import PlagiarismCheck, ReferenceDocument


@admin.register(ReferenceDocument)
class ReferenceDocumentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "source", "created_at")
    search_fields = ("title", "content", "source")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PlagiarismCheck)
class PlagiarismCheckAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "similarity_percent",
        "matched_document",
        "fuzzy_score",
        "tfidf_score",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = ("input_text", "matched_excerpt", "matched_document__title")
    readonly_fields = ("created_at",)
