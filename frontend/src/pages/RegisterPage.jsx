import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerAccount } from "../api";
import { useAuth } from "../auth";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { saveAuth } = useAuth();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("support");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const data = await registerAccount({ login, password, role });
      saveAuth(data);
      navigate("/chat");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="page auth-page">
      <form className="card auth-card" onSubmit={onSubmit}>
        <p className="eyebrow">Новый сотрудник</p>
        <h1>Регистрация</h1>
        <label className="field">
          <span>Логин</span>
          <input
            value={login}
            minLength={3}
            onChange={(event) => setLogin(event.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>Пароль</span>
          <input
            type="password"
            minLength={6}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        <label className="field">
          <span>Роль</span>
          <select value={role} onChange={(event) => setRole(event.target.value)}>
            <option value="support">Техподдержка</option>
            <option value="auction_manager">Менеджер аукциона</option>
          </select>
        </label>
        <p className="muted small">
          Техподдержка спрашивает про машины. Менеджер аукциона ещё и бронирует лоты.
        </p>
        {error && <p className="error">{error}</p>}
        <button className="btn primary" type="submit" disabled={pending}>
          {pending ? "Создаём..." : "Создать аккаунт"}
        </button>
        <p className="muted small">
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </form>
    </div>
  );
}
