import { useEffect, useRef, useState } from "react";
import { Navigate } from "react-router-dom";
import {
  createChatSession,
  deleteChatSession,
  getChatSession,
  listChatSessions,
  sendChatMessage,
} from "../api";
import { ROLE_LABELS, useAuth } from "../auth";
import { formatWhen } from "../format";

function renderRichText(text) {
  const chunks = String(text).split(/(\*\*[^*]+\*\*)/g);
  return chunks.map((chunk, index) => {
    if (chunk.startsWith("**") && chunk.endsWith("**")) {
      return <strong key={index}>{chunk.slice(2, -2)}</strong>;
    }
    return chunk;
  });
}

const SUGGESTIONS = [
  "Какие BMW сейчас доступны?",
  "Сколько стоит Toyota Camry?",
  "Покажи забронированные лоты",
];

export default function ChatPage() {
  const { user, ready } = useAuth();
  const [sessions, setSessions] = useState([]);
  const [query, setQuery] = useState("");
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const threadRef = useRef(null);

  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;
    listChatSessions(query)
      .then((rows) => {
        if (!cancelled) setSessions(rows);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [user, query]);

  useEffect(() => {
    const node = threadRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [messages, pending]);

  if (!ready) {
    return (
      <div className="page">
        <p className="muted">Проверяем сессию...</p>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;

  async function openSession(id) {
    setError("");
    setActiveId(id);
    try {
      const detail = await getChatSession(id);
      setMessages(detail.messages);
    } catch (err) {
      setError(err.message);
    }
  }

  async function onCreate() {
    setError("");
    try {
      const session = await createChatSession();
      setSessions((prev) => [session, ...prev.filter((item) => item.id !== session.id)]);
      setActiveId(session.id);
      setMessages([]);
      setDraft("");
    } catch (err) {
      setError(err.message);
    }
  }

  async function onDelete(id) {
    setError("");
    try {
      await deleteChatSession(id);
      setSessions((prev) => prev.filter((item) => item.id !== id));
      if (activeId === id) {
        setActiveId(null);
        setMessages([]);
      }
    } catch (err) {
      setError(err.message);
    }
  }

  async function onSend(event) {
    event.preventDefault();
    const content = draft.trim();
    if (!content || pending) return;
    setError("");
    let sessionId = activeId;
    setPending(true);
    try {
      if (!sessionId) {
        const session = await createChatSession();
        sessionId = session.id;
        setActiveId(sessionId);
      }
      setDraft("");
      setMessages((prev) => [
        ...prev,
        { id: `local-${Date.now()}`, role: "user", content, created_at: new Date().toISOString() },
      ]);
      const detail = await sendChatMessage(sessionId, content);
      setMessages(detail.messages);
      setSessions((prev) => {
        const next = prev.filter((item) => item.id !== detail.id);
        return [detail, ...next];
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }

  function onKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <div className="chat-page">
      <aside className="chat-side">
        <button type="button" className="btn primary new-chat" onClick={onCreate}>
          Новый чат
        </button>
        <label className="search-field">
          <span className="sr-only">Поиск по истории</span>
          <input
            value={query}
            placeholder="Поиск по истории"
            onChange={(event) => setQuery(event.target.value)}
          />
        </label>
        <div className="session-list">
          {sessions.length === 0 && <p className="muted small">Пока нет диалогов</p>}
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`session-row ${session.id === activeId ? "active" : ""}`}
            >
              <button type="button" className="session-open" onClick={() => openSession(session.id)}>
                <strong>{session.title}</strong>
                <span>{session.preview || "Пустой чат"}</span>
                <time>{formatWhen(session.updated_at)}</time>
              </button>
              <button
                type="button"
                className="session-delete"
                aria-label="Удалить чат"
                onClick={() => onDelete(session.id)}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      <section className="chat-main">
        <header className="chat-head">
          <div>
            <p className="eyebrow">Чат с ИИ</p>
            <h1>{ROLE_LABELS[user.role] || user.role}</h1>
          </div>
        </header>

        <div className="chat-thread" ref={threadRef}>
          {messages.length === 0 && !pending && (
            <div className="chat-empty">
              <h2>Спросите про машины на аукционе</h2>
              <p className="muted">Ассистент смотрит каталог, цену и статус. История хранится в этой сессии.</p>
              <div className="suggestions">
                {SUGGESTIONS.map((text) => (
                  <button key={text} type="button" className="chip" onClick={() => setDraft(text)}>
                    {text}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((message) => (
            <article key={message.id} className={`bubble ${message.role}`}>
              <p>{renderRichText(message.content)}</p>
            </article>
          ))}
          {pending && (
            <article className="bubble assistant pending">
              <p>Смотрю каталог...</p>
            </article>
          )}
        </div>

        {error && <p className="error chat-error">{error}</p>}

        <form className="composer" onSubmit={onSend}>
          <textarea
            rows={2}
            value={draft}
            placeholder="Напишите вопрос и нажмите Enter"
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
          />
          <button className="btn primary" type="submit" disabled={pending || !draft.trim()}>
            Отправить
          </button>
        </form>
      </section>
    </div>
  );
}
