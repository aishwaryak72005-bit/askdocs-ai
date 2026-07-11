import { useEffect, useRef, useState } from "react";
import { Send, FileText, Layers, MessageSquareText } from "lucide-react";
import api from "../api/axios";
import { groupSourcesByFile } from "../utils/sources";

export default function Chat() {
  const [documents, setDocuments] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(null); // null = all documents
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  useEffect(() => {
    api.get("/documents").then(({ data }) => setDocuments(data));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
      const detail = err.response?.data?.detail || "Something went wrong answering that.";
      setMessages((prev) => [...prev, { role: "answer", text: detail, id: Date.now() + 1 }]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: "1.4rem" }}>Ask your documents</h2>

      {documents.length === 0 ? (
        <div className="empty-state">
          <MessageSquareText size={32} className="empty-state-icon" strokeWidth={1.4} />
          Upload a PDF from the Documents page before asking questions.
        </div>
      ) : (
        <div className="chat-shell">
          <div className="chat-doc-list">
            <div className="chat-doc-list-label">Scope</div>
            <button
              className={`chat-doc-item ${selectedDocId === null ? "active" : ""}`}
              onClick={() => setSelectedDocId(null)}
            >
              <Layers size={14} />
              <span className="doc-item-name">All documents</span>
            </button>
            {documents.map((doc) => (
              <button
                key={doc.id}
                className={`chat-doc-item ${selectedDocId === doc.id ? "active" : ""}`}
                onClick={() => setSelectedDocId(doc.id)}
                title={doc.file_name}
              >
                <FileText size={14} />
                <span className="doc-item-name">{doc.file_name}</span>
              </button>
            ))}
          </div>

          <div className="chat-column">
            <div className="chat-messages">
              {messages.length === 0 && (
                <div className="empty-state">
                  Ask a question about {selectedDocId ? "this document" : "your uploaded documents"}.
                </div>
              )}
              {messages.map((m) => (
                <div className={`chat-bubble ${m.role}`} key={m.id}>
                  <div className="bubble-label">{m.role === "question" ? "You" : "DocuMind"}</div>
                  <div className="bubble-content">{m.text}</div>
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
                  <div className="bubble-label">DocuMind</div>
                  <div className="bubble-content">
                    <span className="thinking">
                      <span className="spinner-dot" />
                      <span className="spinner-dot" />
                      <span className="spinner-dot" />
                      &nbsp;thinking…
                    </span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {error && <div className="error-banner">{error}</div>}

            <form className="chat-input-row" onSubmit={handleAsk}>
              <input
                className="form-control"
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
                <Send size={14} /> Ask
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
