import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { ROLE_LABELS, useAuth } from "./auth";
import AuctionDetailPage from "./pages/AuctionDetailPage";
import AuctionListPage from "./pages/AuctionListPage";
import ChatPage from "./pages/ChatPage";
import EvaluatePage from "./pages/EvaluatePage";
import HomePage from "./pages/HomePage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

export default function App() {
  const { user, ready, logout } = useAuth();
  const location = useLocation();
  const chatLayout = location.pathname.startsWith("/chat");

  return (
    <div className="app">
      <header className="topbar">
        <NavLink to="/" className="logo">
          Car Estimate
        </NavLink>
        <nav className="nav-links">
          <NavLink to="/evaluate">Оценка</NavLink>
          <NavLink to="/auction">Аукцион</NavLink>
          {user && <NavLink to="/chat">Чат с ИИ</NavLink>}
        </nav>
        <div className="nav-auth">
          {!ready ? null : user ? (
            <>
              <span className="who">
                {user.login}
                <small>{ROLE_LABELS[user.role] || user.role}</small>
              </span>
              <button type="button" className="btn ghost" onClick={logout}>
                Выйти
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login" className="btn ghost">
                Войти
              </NavLink>
              <NavLink to="/register" className="btn primary">
                Регистрация
              </NavLink>
            </>
          )}
        </div>
      </header>
      <main className={chatLayout ? "main-chat" : ""}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/evaluate" element={<EvaluatePage />} />
          <Route path="/auction" element={<AuctionListPage />} />
          <Route path="/auction/:id" element={<AuctionDetailPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
