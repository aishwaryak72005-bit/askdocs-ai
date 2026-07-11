from rest_framework import serializers
from .models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = [
            "id", "file_name", "page_count", "summary", "uploaded_at",
            "indexed", "chunk_count", "index_error",
        ]


class DocumentUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ["id", "file_name", "file", "page_count", "uploaded_at"]
        read_only_fields = ["file_name", "page_count", "uploaded_at"]
