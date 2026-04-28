from django.db import models


class ReferenceDocument(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    source = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class PlagiarismCheck(models.Model):
    input_text = models.TextField()
    similarity_percent = models.FloatField(default=0)
    matched_document = models.ForeignKey(
        ReferenceDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="checks",
    )
    matched_excerpt = models.TextField(blank=True)
    fuzzy_score = models.FloatField(default=0)
    tfidf_score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"PlagiarismCheck #{self.id} - {self.similarity_percent:.1f}%"
