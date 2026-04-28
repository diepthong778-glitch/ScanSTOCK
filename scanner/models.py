from django.db import models


class ScanJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    class RiskLevel(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"
        UNKNOWN = "unknown", "Unknown"

    DOCUMENT_STATUS = [
        ("pending", "Pending"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    original_image = models.ImageField(upload_to="scanner/originals/")
    scanned_image = models.ImageField(upload_to="scanner/results/", null=True, blank=True)
    pdf_file = models.FileField(upload_to="scanner/pdfs/", null=True, blank=True)

    ocr_text = models.TextField(blank=True)
    document_type = models.CharField(max_length=100, blank=True)
    document_confidence = models.FloatField(default=0)

    fake_risk_score = models.FloatField(default=0)
    fake_risk_level = models.CharField(max_length=50, blank=True)
    fake_reasons = models.JSONField(default=list, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"ScanJob #{self.id} - {self.document_type or 'Unknown'}"
