from django.urls import path
from .views import AskQuestionView, ChatHistoryView, DocumentSummaryView

urlpatterns = [
    path("ask", AskQuestionView.as_view(), name="ask"),
    path("history", ChatHistoryView.as_view(), name="history"),
    path("summary/<int:document_id>", DocumentSummaryView.as_view(), name="summary"),
]
