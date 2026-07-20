import { useEffect, useRef, useState } from "react";
import { Send, FileText, Layers, MessageSquareText, RefreshCw, Trash2 } from "lucide-react";
import api from "../api/axios";
import { groupSourcesByFile } from "../utils/sources";
import FormattedMarkdown from "../components/FormattedMarkdown";

export default function Chat() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null); // null = all documents
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    // Fetch documents
    api.get("/documents").then(({ data }) => setDocuments(data)).catch(() => {});

    // Fetch user's persistent Q&A history
    api.get("/history")
      .then(({ data }) => {
        const historyMessages = [];
        data.forEach((item) => {
          historyMessages.push({
            role: "question",
            text: item.question,
            id: `q_${item.id}`,
          });
          historyMessages.push({
            role: "answer",
            text: item.answer,
            sources: item.sources,
            id: `a_${item.id}`,
          });
        });
        setMessages(historyMessages);
      })
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, asking]);

  async function handleAsk(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setError("");
    setQuestion("");
    setMessages((prev) => [...prev, { role: "question", text: q, id: Date.now() }]);
    setAsking(true);
    try {
      const { data } = await api.post("/ask", {
        question: q,
        document_id: selectedDocId || undefined,
      });
      setMessages((prev) => [
        ...prev,
        { role: "answer", text: data.answer, sources: data.sources, id: data.id },
      ]);
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || "Something went wrong answering that.";
      setMessages((prev) => [...prev, { role: "answer", text: detail, id: Date.now() + 1 }]);
    } finally {
      setAsking(false);
    }
  }

  function handleClearScreen() {
    setMessages([]);
  }

  return (
    <div className="page-container enter">
      <div className="page-header-row">
        <div>
          <h2>Ask your documents</h2>
          <p className="page-sub">Retrieval-grounded Q&amp;A powered by AskDocs AI</p>
        </div>
        {messages.length > 0 && (
          <button className="btn btn-sm btn-outline-secondary btn-icon" onClick={handleClearScreen}>
            <Trash2 size={14} /> Clear View
          </button>
        )}
      </div>

      {documents.length === 0 ? (
        <div className="empty-state glass-card">
          <MessageSquareText size={36} className="empty-state-icon" strokeWidth={1.4} />
          <p>Upload a PDF from the <strong>Documents</strong> page before asking questions.</p>
        </div>
      ) : (
        <div className="chat-shell">
          <div className="chat-doc-list glass-card">
            <div className="chat-doc-list-label">Scope</div>
            <button
              className={`chat-doc-item ${selectedDocId === null ? "active" : ""}`}
              onClick={() => setSelectedDocId(null)}
            >
              <Layers size={15} />
              <span className="doc-item-name">All documents</span>
            </button>
            {documents.map((doc) => (
              <button
                key={doc.id}
                className={`chat-doc-item ${selectedDocId === doc.id ? "active" : ""}`}
                onClick={() => setSelectedDocId(doc.id)}
                title={doc.file_name}
              >
                <FileText size={15} />
                <span className="doc-item-name">{doc.file_name}</span>
              </button>
            ))}
          </div>

          <div className="chat-column">
            <div className="chat-messages glass-card">
              {loadingHistory && (
                <div className="text-center p-3 text-muted">
                  <RefreshCw size={18} className="spin-icon" /> Loading conversation history…
                </div>
              )}
              {!loadingHistory && messages.length === 0 && (
                <div className="empty-state">
                  Ask a question about {selectedDocId ? "this document" : "your uploaded documents"}.
                </div>
              )}
              {messages.map((m) => (
                <div className={`chat-bubble ${m.role}`} key={m.id}>
                  <div className="bubble-label">{m.role === "question" ? "You" : "AskDocs AI"}</div>
                  <div className="bubble-content">
                    {m.role === "answer" ? (
                      <FormattedMarkdown content={m.text} />
                    ) : (
                      m.text
                    )}
                  </div>
                  {m.role === "answer" && m.sources?.length > 0 && (
                    <div className="source-tags">
                      {groupSourcesByFile(m.sources).map((s, i) => (
                        <span className="source-tag" key={i}>
                          {s.file_name} · p.{s.pages.join(", ")}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
              {asking && (
                <div className="chat-bubble answer">
                  <div className="bubble-label">AskDocs AI</div>
                  <div className="bubble-content">
                    <span className="thinking">
                      <span className="spinner-dot" />
                      <span className="spinner-dot" />
                      <span className="spinner-dot" />
                      &nbsp;Analyzing &amp; generating answer…
                    </span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {error && <div className="error-banner mt-2">{error}</div>}

            <form className="chat-input-row" onSubmit={handleAsk}>
              <input
                className="form-control chat-input"
                placeholder="Ask a question about your documents…"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                disabled={asking}
              />
              <button
                className="btn btn-primary btn-icon"
                type="submit"
                disabled={asking || !question.trim()}
              >
                <Send size={15} /> Ask
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
