import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { BookMarked, AlertCircle, Mail, Lock, User, ArrowRight, Sparkles, Layers, CheckCircle2 } from "lucide-react";
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
    <div className="auth-hero-container">
      {/* Background ambient lighting */}
      <div className="ambient-orb orb-1" />
      <div className="ambient-orb orb-2" />

      <div className="auth-content-grid">
        {/* Left Side: Brand Showcase */}
        <div className="auth-brand-side enter">
          <div className="brand-badge">
            <Sparkles size={14} /> Get Started in Seconds
          </div>
          
          <h1 className="auth-hero-title">
            Unlock AI Search for <span className="gradient-text">Your PDF Library.</span>
          </h1>

          <p className="auth-hero-desc">
            Create a free account to upload up to 10 PDFs, index text chunks, and retrieve grounded answers in real-time.
          </p>

          <div className="feature-cards-grid">
            <div className="feature-pill-card">
              <Layers className="feature-icon" size={20} />
              <div>
                <strong>Multi-Document Scope</strong>
                <p>Query across individual PDFs or your entire library</p>
              </div>
            </div>

            <div className="feature-pill-card">
              <CheckCircle2 className="feature-icon" size={20} />
              <div>
                <strong>Instant Setup</strong>
                <p>No complex configuration — ready in 10 seconds</p>
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
              <h2>Create Account</h2>
              <p>Start asking questions across your documents</p>
            </div>

            {error && (
              <div className="error-banner">
                <AlertCircle size={16} /> {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="input-group-custom">
                <label>Your Name</label>
                <div className="input-with-icon">
                  <User className="field-icon" size={18} />
                  <input
                    type="text"
                    className="form-control-custom"
                    placeholder="Alex Smith"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
              </div>

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
                    placeholder="At least 8 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    minLength={8}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-glow-primary" disabled={loading}>
                {loading ? (
                  "Creating Account…"
                ) : (
                  <>
                    Create Account <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            <div className="auth-footer-link">
              Already have an account? <Link to="/login">Sign in</Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
