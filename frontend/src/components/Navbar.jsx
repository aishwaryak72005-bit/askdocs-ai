import { Link, NavLink, useNavigate } from "react-router-dom";
import { BookMarked, FileStack, MessageCircleQuestion, History, LogOut } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <header className="topbar">
      <Link to="/" className="brand">
        <span className="brand-icon">
          <BookMarked size={20} strokeWidth={2.2} />
        </span>
        Docu<span className="brand-mark">Mind</span>
      </Link>
      <nav className="nav-links">
        <NavLink to="/" end className={({ isActive }) => (isActive ? "active" : "")}>
          <FileStack size={15} /> Documents
        </NavLink>
        <NavLink to="/chat" className={({ isActive }) => (isActive ? "active" : "")}>
          <MessageCircleQuestion size={15} /> Ask
        </NavLink>
        <NavLink to="/history" className={({ isActive }) => (isActive ? "active" : "")}>
          <History size={15} /> History
        </NavLink>
        <button
          onClick={handleLogout}
          className="btn btn-sm btn-outline-secondary btn-icon"
          style={{ marginLeft: "0.8rem" }}
        >
          <LogOut size={14} />
          {user?.name ? user.name : "Log out"}
        </button>
      </nav>
    </header>
  );
}
