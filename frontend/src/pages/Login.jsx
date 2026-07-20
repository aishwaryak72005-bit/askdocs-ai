import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookMarked, AlertCircle, Mail, Lock, ArrowRight, Sparkles, FileSearch, ShieldCheck } from "lucide-react";
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
    <div className="auth-hero-container">
      {/* Background ambient lighting */}
      <div className="ambient-orb orb-1" />
      <div className="ambient-orb orb-2" />

      <div className="auth-content-grid">
        {/* Left Side: Brand Showcase */}
        <div className="auth-brand-side enter">
          <div className="brand-badge">
            <Sparkles size={14} /> Powered by Gemini 2.0 &amp; RAG
          </div>
          
          <h1 className="auth-hero-title">
            Ask Questions Across <span className="gradient-text">All Your PDFs.</span>
          </h1>

          <p className="auth-hero-desc">
            Upload your documents and get instant, accurate answers with exact page-level citations — so you always know where facts come from.
          </p>

          <div className="feature-cards-grid">
            <div className="feature-pill-card">
              <FileSearch className="feature-icon" size={20} />
              <div>
                <strong>Page-Level Citations</strong>
                <p>Every response links to exact pages</p>
              </div>
            </div>

            <div className="feature-pill-card">
              <ShieldCheck className="feature-icon" size={20} />
              <div>
                <strong>Isolated Vector Store</strong>
                <p>Your documents stay private to your account</p>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side: Modern Glass Form */}
        <div className="auth-card-side enter">
          <div className="auth-glass-card">
            <div className="auth-header">
              <div className="auth-logo">
                <BookMarked size={22} />
              </div>
              <h2>Welcome Back</h2>
              <p>Sign in to access your document library</p>
            </div>

            {error && (
              <div className="error-banner">
                <AlertCircle size={16} /> {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="input-group-custom">
                <label>Email Address</label>
                <div className="input-with-icon">
                  <Mail className="field-icon" size={18} />
                  <input
                    type="email"
                    className="form-control-custom"
                    placeholder="name@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                  />
                </div>
              </div>

              <div className="input-group-custom">
                <label>Password</label>
                <div className="input-with-icon">
                  <Lock className="field-icon" size={18} />
                  <input
                    type="password"
                    className="form-control-custom"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-glow-primary" disabled={loading}>
                {loading ? (
                  "Signing in…"
                ) : (
                  <>
                    Sign In <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-footer-link">
              Don't have an account? <Link to="/register">Create one for free</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
