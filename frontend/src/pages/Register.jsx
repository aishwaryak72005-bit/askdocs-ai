import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookMarked, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register(name, email, password);
      navigate("/");
    } catch (err) {
      const data = err.response?.data;
      const msg = data?.email?.[0] || data?.password?.[0] || data?.detail || "Registration failed.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrap">
      <div className="auth-panel">
        <Link to="/login" className="auth-panel-brand">
          <BookMarked size={22} /> AskDocs AI
        </Link>

        <div className="stamp-float s1">notice-period · p.2</div>
        <div className="stamp-float s2">contract.pdf</div>
        <div className="stamp-float s3">summary · ready</div>

        <div className="auth-panel-copy">
          <h2>Your documents, indexed and ready.</h2>
          <p>
            Drop in up to ten PDFs. AskDocs AI chunks, embeds, and indexes
            each one so you can ask across all of them at once — and get
            answers you can actually verify.
          </p>
        </div>

        <div className="auth-panel-footer">askdocs ai — retrieval-grounded Q&amp;A</div>
      </div>

      <div className="auth-form-side">
        <div className="auth-card enter">
          <h1>Create an account</h1>
          <p className="auth-sub">Start asking questions across your PDFs.</p>

          {error && (
            <div className="error-banner">
              <AlertCircle size={16} /> {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="mb-3">
              <label className="form-label">Name</label>
              <input
                type="text"
                className="form-control"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Email</label>
              <input
                type="email"
                className="form-control"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="mb-3">
              <label className="form-label">Password</label>
              <input
                type="password"
                className="form-control"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
              <div className="form-text">At least 8 characters.</div>
            </div>
            <button type="submit" className="btn btn-primary w-100" disabled={loading}>
              {loading ? "Creating account…" : "Create account"}
            </button>
          </form>

          <div className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
