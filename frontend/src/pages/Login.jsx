import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookMarked, AlertCircle } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Check your credentials.");
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

        <div className="stamp-float s1">ask · p.12</div>
        <div className="stamp-float s2">hr-policy.pdf</div>
        <div className="stamp-float s3">cited · p.3</div>

        <div className="auth-panel-copy">
          <h2>Every answer, traced to its page.</h2>
          <p>
            Upload your PDFs and ask questions in plain language. AskDocs AI
            retrieves the exact passages behind each answer, so you always
            know where it came from.
          </p>
        </div>

        <div className="auth-panel-footer">askdocs ai — retrieval-grounded Q&amp;A</div>
      </div>

      <div className="auth-form-side">
        <div className="auth-card enter">
          <h1>Welcome back</h1>
          <p className="auth-sub">Sign in to keep working with your documents.</p>

          {error && (
            <div className="error-banner">
              <AlertCircle size={16} /> {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
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
                required
              />
            </div>
            <button type="submit" className="btn btn-primary w-100" disabled={loading}>
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <div className="auth-switch">
            No account yet? <Link to="/register">Create one</Link>
          </div>
        </div>
      </div>
    </div>
  );
}
