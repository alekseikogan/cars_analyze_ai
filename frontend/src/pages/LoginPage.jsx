import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginAccount } from "../api";
import { useAuth } from "../auth";

export default function LoginPage() {
  const navigate = useNavigate();
  const { saveAuth } = useAuth();
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function onSubmit(event) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const data = await loginAccount({ login, password });
      saveAuth(data);
      navigate("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="page auth-page">
      <form className="card auth-card" onSubmit={onSubmit}>
        <p className="eyebrow">Личный кабинет</p>
        <h1>Вход</h1>
        <label className="field">
          <span>Логин</span>
          <input value={login} onChange={(event) => setLogin(event.target.value)} required />
        </label>
        <label className="field">
          <span>Пароль</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn primary" type="submit" disabled={pending}>
          {pending ? "Входим..." : "Войти"}
        </button>
        <p className="muted small">
          Нет аккаунта? <Link to="/register">Зарегистрироваться</Link>
        </p>
        <p className="muted small">
          Демо: support / support123 — техподдержка, manager / manager123 — менеджер аукциона.
        </p>
      </form>
    </div>
  );
}
