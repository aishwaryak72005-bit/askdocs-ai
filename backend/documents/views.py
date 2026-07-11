from django.conf import settings
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Document
from .serializers import DocumentSerializer
from .utils import extract_text_from_pdf, chunk_text
from chat.gemini_client import embed_documents
from chat.vectorstore import add_chunks, delete_document_chunks


class UploadDocumentsView(APIView):
    """
    POST /api/upload
    Accepts one or more PDF files under the 'files' form field.
    Enforces MAX_PDF_COUNT_PER_USER and MAX_PDF_SIZE_MB from settings.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        files = request.FILES.getlist("files")
        if not files:
            return Response({"detail": "No files provided."}, status=status.HTTP_400_BAD_REQUEST)

        existing_count = Document.objects.filter(user=request.user).count()
        if existing_count + len(files) > settings.MAX_PDF_COUNT_PER_USER:
            return Response(
                {"detail": f"Upload limit exceeded. Max {settings.MAX_PDF_COUNT_PER_USER} PDFs per user."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        max_bytes = settings.MAX_PDF_SIZE_MB * 1024 * 1024
        created_docs = []
        errors = []

        for f in files:
            if not f.name.lower().endswith(".pdf"):
                errors.append(f"{f.name}: not a PDF file.")
                continue
            if f.size > max_bytes:
                errors.append(f"{f.name}: exceeds {settings.MAX_PDF_SIZE_MB}MB limit.")
                continue

            doc = Document.objects.create(user=request.user, file_name=f.name, file=f)
            try:
                doc.file.open("rb")
                text, page_count = extract_text_from_pdf(doc.file)
                doc.extracted_text = text
                doc.page_count = page_count
                doc.save()
            except Exception as e:
                errors.append(f"{f.name}: failed to extract text ({e}).")
                created_docs.append(doc)
                continue
            finally:
                doc.file.close()

            # Index into the vector store for RAG retrieval. Kept separate
            # from extraction so upload still succeeds even if embedding
            # fails (e.g. AI API hiccup) — the doc just won't be searchable
            # via RAG yet and index_error explains why.
            try:
                chunks = chunk_text(
                    doc.extracted_text,
                    chunk_size=settings.CHUNK_SIZE_CHARS,
                    overlap=settings.CHUNK_OVERLAP_CHARS,
                )
                if chunks:
                    vectors = embed_documents([c["text"] for c in chunks])
                    add_chunks(doc.id, request.user.id, doc.file_name, chunks, vectors)
                    doc.indexed = True
                    doc.chunk_count = len(chunks)
                else:
                    doc.index_error = "No extractable text to index."
                doc.save(update_fields=["indexed", "chunk_count", "index_error"])
            except Exception as e:
                doc.index_error = f"Indexing failed: {e}"
                doc.save(update_fields=["index_error"])
                errors.append(f"{f.name}: uploaded, but AI indexing failed ({e}).")

            created_docs.append(doc)

        return Response(
            {
                "uploaded": DocumentSerializer(created_docs, many=True).data,
                "errors": errors,
            },
            status=status.HTTP_201_CREATED if created_docs else status.HTTP_400_BAD_REQUEST,
        )


class DocumentListView(APIView):
    """GET /api/documents — list current user's uploaded PDFs."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        docs = Document.objects.filter(user=request.user)
        return Response(DocumentSerializer(docs, many=True).data)


class DocumentDeleteView(APIView):
    """DELETE /api/document/{id} — remove a PDF (and its file from disk)."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, doc_id):
        try:
            doc = Document.objects.get(id=doc_id, user=request.user)
        except Document.DoesNotExist:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        doc.file.delete(save=False)
        doc.delete()
        try:
            delete_document_chunks(doc_id)
        except Exception:
            pass  # vector store cleanup is best-effort; doc record is already gone
        return Response(status=status.HTTP_204_NO_CONTENT)
