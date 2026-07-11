from django.db import models
from django.contrib.auth.models import User


def upload_path(instance, filename):
    return f"pdfs/{instance.user_id}/{filename}"


class Document(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="documents")
    file_name = models.CharField(max_length=255)
    file = models.FileField(upload_to=upload_path)
    extracted_text = models.TextField(blank=True, default="")
    page_count = models.IntegerField(default=0)
    summary = models.TextField(blank=True, default="")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # RAG indexing status. A document can be uploaded and text-extracted
    # successfully even if embedding/indexing fails (e.g. AI API hiccup),
    # so these are tracked separately from the upload itself.
    indexed = models.BooleanField(default=False)
    chunk_count = models.IntegerField(default=0)
    index_error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.file_name
