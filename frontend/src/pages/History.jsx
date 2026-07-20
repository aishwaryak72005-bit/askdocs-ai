import { useEffect, useState } from "react";
import { Clock, FileText, Layers, Archive } from "lucide-react";
import api from "../api/axios";
import { groupSourcesByFile } from "../utils/sources";
import FormattedMarkdown from "../components/FormattedMarkdown";

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
    <div className="page-container enter">
      <div className="page-header-row">
        <div>
          <h2>Chat history</h2>
          <p className="page-sub">Review past Q&amp;A sessions and cited sources</p>
        </div>
      </div>

      {error && <div className="error-banner">{error}</div>}

      {loading ? (
        <div className="empty-state">Loading…</div>
      ) : messages.length === 0 ? (
        <div className="empty-state glass-card">
          <Archive size={36} className="empty-state-icon" strokeWidth={1.4} />
          <p>No questions asked yet.</p>
        </div>
      ) : (
        <div className="d-flex flex-column gap-3">
          {messages.map((m) => (
            <div key={m.id} className="history-item glass-card p-4 enter">
              <div className="history-meta mb-2">
                <Clock size={13} />
                {formatDate(m.timestamp)}
                <span style={{ opacity: 0.5 }}>·</span>
                {m.document_name ? (
                  <>
                    <FileText size={13} /> {m.document_name}
                  </>
                ) : (
                  <>
                    <Layers size={13} /> All documents
                  </>
                )}
              </div>
              <div className="history-question mb-2 text-info font-weight-bold">
                Q: {m.question}
              </div>
              <div className="history-answer">
                <FormattedMarkdown content={m.answer} />
              </div>
              {m.sources?.length > 0 && (
                <div className="source-tags mt-3">
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
