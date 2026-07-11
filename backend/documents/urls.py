from django.urls import path
from .views import UploadDocumentsView, DocumentListView, DocumentDeleteView

urlpatterns = [
    path("upload", UploadDocumentsView.as_view(), name="upload"),
    path("documents", DocumentListView.as_view(), name="documents"),
    path("document/<int:doc_id>", DocumentDeleteView.as_view(), name="document_delete"),
]
