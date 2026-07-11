from rest_framework import serializers
from .models import ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    document_name = serializers.CharField(source="document.file_name", read_only=True, default=None)

    class Meta:
        model = ChatMessage
        fields = ["id", "document", "document_name", "question", "answer", "sources", "timestamp"]
