from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from documents.models import Document
from .models import ChatMessage
from .serializers import ChatMessageSerializer
from .gemini_client import ask_question, generate_summary
from .retrieval import retrieve_context


class AskQuestionView(APIView):
    """
    POST /api/ask
    Body: { "question": "...", "document_id": <int, optional> }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        question = request.data.get("question", "").strip()
        document_id = request.data.get("document_id")

        if not question:
            return Response({"detail": "Question is required."}, status=status.HTTP_400_BAD_REQUEST)

        doc = None
        if document_id:
            try:
                doc = Document.objects.get(id=document_id, user=request.user)
            except Document.DoesNotExist:
                return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        elif not Document.objects.filter(user=request.user).exists():
            return Response({"detail": "No documents uploaded yet."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            context_text, sources = retrieve_context(
                question, user_id=request.user.id, document_id=document_id
            )
        except Exception as e:
            return Response({"detail": f"AI request failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        if not context_text:
            return Response(
                {"detail": "No indexed content found for that document yet. Try re-uploading it."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Retrieve recent chat history for context (up to 5 past messages)
        recent_history = list(
            ChatMessage.objects.filter(user=request.user)
            .order_by("-created_at")[:5]
        )
        recent_history.reverse()

        try:
            answer = ask_question(context_text, question, history=recent_history)
        except Exception as e:
            return Response({"detail": f"AI request failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        chat_message = ChatMessage.objects.create(
            user=request.user,
            document=doc,
            question=question,
            answer=answer,
            sources=sources,
        )
        return Response(ChatMessageSerializer(chat_message).data, status=status.HTTP_201_CREATED)


class ChatHistoryView(APIView):
    """GET /api/history — list the current user's past Q&A."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        messages = ChatMessage.objects.filter(user=request.user).order_by("created_at")
        return Response(ChatMessageSerializer(messages, many=True).data)


class DocumentSummaryView(APIView):
    """GET /api/summary/{document_id} — generate (and cache) a document summary."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, document_id):
        try:
            doc = Document.objects.get(id=document_id, user=request.user)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if doc.summary:
            return Response({"document_id": doc.id, "summary": doc.summary})

        try:
            summary = generate_summary(doc.extracted_text)
        except Exception as e:
            return Response({"detail": f"AI request failed: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        doc.summary = summary
        doc.save(update_fields=["summary"])
        return Response({"document_id": doc.id, "summary": summary})
