from django.contrib import admin

from scanner.models import ScanJob


@admin.register(ScanJob)
class ScanJobAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "document_type",
        "document_confidence",
        "fake_risk_level",
        "fake_risk_score",
        "created_at",
    )
    list_filter = ("status", "document_type", "fake_risk_level", "created_at")
    search_fields = ("ocr_text", "error_message")
    readonly_fields = ("created_at", "updated_at")
