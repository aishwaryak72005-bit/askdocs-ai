import { useEffect, useRef, useState } from "react";
import { UploadCloud, FileText, Sparkles, Trash2, AlertCircle, Inbox, X } from "lucide-react";
import api from "../api/axios";

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

export default function Dashboard() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState("");
  const [summaryDoc, setSummaryDoc] = useState(null);
  const [summaryText, setSummaryText] = useState("");
  const [summaryLoading, setSummaryLoading] = useState(false);
  const fileInputRef = useRef(null);

  async function loadDocuments() {
    setLoading(true);
    try {
      const { data } = await api.get("/documents");
      setDocuments(data);
    } catch {
      setError("Couldn't load your documents.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function uploadFiles(fileList) {
    const files = Array.from(fileList);
    if (!files.length) return;
    setError("");
    setUploading(true);
    const formData = new FormData();
    files.forEach((f) => formData.append("files", f));
    try {
      const { data } = await api.post("/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      if (data.errors?.length) {
        setError(data.errors.join(" "));
      }
      await loadDocuments();
    } catch (err) {
      setError(err.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this document? This can't be undone.")) return;
    try {
      await api.delete(`/document/${id}`);
      setDocuments((docs) => docs.filter((d) => d.id !== id));
    } catch {
      setError("Couldn't delete that document.");
    }
  }

  async function handleSummarize(doc) {
    setSummaryDoc(doc);
    setSummaryText("");
    setSummaryLoading(true);
    try {
      const { data } = await api.get(`/summary/${doc.id}`);
      setSummaryText(data.summary);
    } catch {
      setSummaryText("Couldn't generate a summary right now.");
    } finally {
      setSummaryLoading(false);
    }
  }

  return (
    <div className="page-container">
      <div className="section-heading">
        <h2>Your documents</h2>
        <span className="count-pill">{documents.length}/10 uploaded</span>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle size={16} /> {error}
        </div>
      )}

      <div
        className={`upload-zone ${dragging ? "dragging" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          uploadFiles(e.dataTransfer.files);
        }}
        onClick={() => fileInputRef.current?.click()}
        role="button"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          multiple
          hidden
          onChange={(e) => uploadFiles(e.target.files)}
        />
        <div className="upload-zone-icon">
          <UploadCloud size={28} strokeWidth={1.6} />
        </div>
        {uploading ? (
          <span>Uploading and indexing…</span>
        ) : (
          <>
            <strong>Drop PDFs here</strong> or click to browse
            <div className="upload-zone-hint">Up to 10 files, 20MB each</div>
          </>
        )}
      </div>

      {loading ? (
        <div className="empty-state">Loading your documents…</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          <Inbox size={32} className="empty-state-icon" strokeWidth={1.4} />
          No documents yet. Upload a PDF to get started.
        </div>
      ) : (
        <div className="doc-grid">
          {documents.map((doc) => (
            <div className="doc-card enter" key={doc.id}>
              <div className="doc-card-top">
                <div className="doc-card-icon">
                  <FileText size={17} />
                </div>
                <div>
                  <div className="doc-name">{doc.file_name}</div>
                  <div className="doc-meta">
                    {doc.page_count} pages · {formatDate(doc.uploaded_at)}
                  </div>
                </div>
              </div>

              <span className={`index-status ${doc.indexed ? "ready" : "pending"}`}>
                <span className="dot" />
                {doc.indexed ? `Indexed · ${doc.chunk_count} chunks` : "Not indexed"}
              </span>

              <div className="doc-actions">
                <button
                  className="btn btn-sm btn-outline-secondary btn-icon"
                  onClick={() => handleSummarize(doc)}
                >
                  <Sparkles size={13} /> Summarize
                </button>
                <button
                  className="btn btn-sm btn-outline-danger btn-icon"
                  onClick={() => handleDelete(doc.id)}
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {summaryDoc && (
        <div
          className="modal d-block"
          style={{ background: "rgba(26,31,54,0.5)" }}
          onClick={() => setSummaryDoc(null)}
        >
          <div className="modal-dialog modal-dialog-centered" onClick={(e) => e.stopPropagation()}>
            <div className="modal-content">
              <div className="modal-header">
                <h5 className="modal-title font-display d-flex align-items-center gap-2">
                  <Sparkles size={16} style={{ color: "var(--archive)" }} />
                  {summaryDoc.file_name}
                </h5>
                <button className="btn-close" onClick={() => setSummaryDoc(null)} />
              </div>
              <div className="modal-body">
                {summaryLoading ? (
                  <span className="thinking">
                    <span className="spinner-dot" />
                    <span className="spinner-dot" />
                    <span className="spinner-dot" />
                    &nbsp;generating summary…
                  </span>
                ) : (
                  <div style={{ whiteSpace: "pre-wrap" }}>{summaryText}</div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
