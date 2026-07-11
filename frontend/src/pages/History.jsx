import { useEffect, useState } from "react";
import { Clock, FileText, Layers, Archive } from "lucide-react";
import api from "../api/axios";
import { groupSourcesByFile } from "../utils/sources";

function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function History() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/history")
      .then(({ data }) => setMessages(data))
      .catch(() => setError("Couldn't load your chat history."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-container">
      <h2 style={{ marginBottom: "1.4rem" }}>Chat history</h2>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty-state">Loading…</div>
      ) : messages.length === 0 ? (
        <div className="empty-state">
          <Archive size={32} className="empty-state-icon" strokeWidth={1.4} />
          No questions asked yet.
        </div>
      ) : (
        <div>
          {messages.map((m) => (
            <div key={m.id} className="history-item enter">
              <div className="history-meta">
                <Clock size={12} />
                {formatDate(m.timestamp)}
                <span style={{ opacity: 0.5 }}>·</span>
                {m.document_name ? (
                  <>
                    <FileText size={12} /> {m.document_name}
                  </>
                ) : (
                  <>
                    <Layers size={12} /> all documents
                  </>
                )}
              </div>
              <div className="history-question">{m.question}</div>
              <div className="history-answer">{m.answer}</div>
              {m.sources?.length > 0 && (
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
        </div>
      )}
    </div>
  );
}
