import { FileText, Brain, MessageSquare, Shield, History } from "lucide-react";

export default function About() {
  return (
    <div className="about-page">
      <div className="about-hero">
        <h1>AskDocs AI</h1>

        <p>
          Upload PDF documents, ask natural language questions, and receive
          AI-powered answers with accurate citations.
        </p>
      </div>

      <div className="feature-grid">
        <div className="feature-card">
          <FileText size={42} />
          <h3>PDF Upload</h3>
          <p>Upload and organize your documents securely.</p>
        </div>

        <div className="feature-card">
          <Brain size={42} />
          <h3>AI Intelligence</h3>
          <p>Powered by Gemini AI for accurate responses.</p>
        </div>

        <div className="feature-card">
          <MessageSquare size={42} />
          <h3>Ask Questions</h3>
          <p>Chat naturally with your uploaded PDFs.</p>
        </div>

        <div className="feature-card">
          <History size={42} />
          <h3>Conversation History</h3>
          <p>Access previous questions and answers anytime.</p>
        </div>

        <div className="feature-card">
          <Shield size={42} />
          <h3>Secure Access</h3>
          <p>User authentication with protected routes.</p>
        </div>

        <div className="feature-card">
          <Brain size={42} />
          <h3>Source Citations</h3>
          <p>Every answer includes document references.</p>
        </div>
      </div>
    </div>
  );
}
