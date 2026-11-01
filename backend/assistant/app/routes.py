from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.assistant.app.graph import run_chat
from backend.assistant.app.models import ChatMessage, ChatSession, User
from backend.gateway.app.db import get_db
from backend.shared.security import create_token, decode_token, hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter()

ROLES = {"support", "auction_manager"}


class RegisterRequest(BaseModel):
    login: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    role: str


class LoginRequest(BaseModel):
    login: str
    password: str


class UserRead(BaseModel):
    id: int
    login: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: UserRead


class SessionRead(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    title: str
    preview: str
    updated_at: datetime


class MessageRead(BaseModel):
    id: int
    role: str
    content: str
    created_at: datetime


class SessionDetail(SessionRead):
    messages: list[MessageRead]


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Достаёт сотрудника по Bearer-токену."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Нужно войти")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    user = db.get(User, int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Пользователь не найден")
    return user


def _auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        token=create_token(user.id, user.login, user.role),
        user=UserRead(id=user.id, login=user.login, role=user.role),
    )


def _own_session(db: Session, user: User, session_id: str) -> ChatSession:
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Чат не найден")
    return session


@router.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Создаёт сотрудника и сразу открывает сессию."""
    login = payload.login.strip()
    if payload.role not in ROLES:
        raise HTTPException(status_code=400, detail="Выберите роль: техподдержка или менеджер аукциона")
    taken = db.scalar(select(User.id).where(User.login == login))
    if taken is not None:
        raise HTTPException(status_code=409, detail="Такой логин уже занят")
    user = User(login=login, password_hash=hash_password(payload.password), role=payload.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _auth_response(user)


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> AuthResponse:
    """Проверяет логин и пароль и возвращает токен."""
    user = db.scalar(select(User).where(User.login == payload.login.strip()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    return _auth_response(user)


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> UserRead:
    """Возвращает текущего сотрудника."""
    return UserRead(id=user.id, login=user.login, role=user.role)


@router.get("/chat/sessions", response_model=list[SessionRead])
def list_sessions(
    q: str = "",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ChatSession]:
    """Список чатов сотрудника. q ищет по названию и тексту сообщений."""
    stmt = select(ChatSession).where(ChatSession.user_id == user.id)
    query = q.strip()
    if query:
        like = f"%{query}%"
        message_sessions = select(ChatMessage.session_id).where(ChatMessage.content.ilike(like))
        stmt = stmt.where(or_(ChatSession.title.ilike(like), ChatSession.id.in_(message_sessions)))
    stmt = stmt.order_by(ChatSession.updated_at.desc())
    return list(db.scalars(stmt))


@router.post("/chat/sessions", response_model=SessionRead)
def create_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChatSession:
    """Открывает пустую сессию чата."""
    session = ChatSession(id=str(uuid.uuid4()), user_id=user.id, title="Новый чат", preview="")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/chat/sessions/{session_id}", response_model=SessionDetail)
def get_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionDetail:
    """Возвращает сессию и её сообщения."""
    session = _own_session(db, user, session_id)
    messages = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id)
        )
    )
    return SessionDetail(
        id=session.id,
        title=session.title,
        preview=session.preview,
        updated_at=session.updated_at,
        messages=[
            MessageRead(id=item.id, role=item.role, content=item.content, created_at=item.created_at)
            for item in messages
        ],
    )


@router.delete("/chat/sessions/{session_id}")
def delete_session(
    session_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Удаляет сессию сотрудника вместе с сообщениями."""
    session = _own_session(db, user, session_id)
    db.query(ChatMessage).filter(ChatMessage.session_id == session.id).delete()
    db.delete(session)
    db.commit()
    return {"ok": True}


@router.post("/chat/sessions/{session_id}/messages", response_model=SessionDetail)
def send_message(
    session_id: str,
    payload: SendMessageRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SessionDetail:
    """Добавляет вопрос, прогоняет LangGraph и сохраняет ответ в эту сессию."""
    session = _own_session(db, user, session_id)
    history = list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.id)
        )
    )
    question = payload.content.strip()
    lc_messages = []
    for item in history:
        if item.role == "user":
            lc_messages.append(HumanMessage(content=item.content))
        elif item.role == "assistant":
            lc_messages.append(AIMessage(content=item.content))
    lc_messages.append(HumanMessage(content=question))

    db.add(ChatMessage(session_id=session.id, role="user", content=question))
    if session.title == "Новый чат":
        session.title = question[:80]
    session.updated_at = datetime.now(timezone.utc)
    db.commit()

    try:
        answer = run_chat(user.role, lc_messages)
    except Exception as exc:
        logger.exception("chat failed session=%s", session.id)
        answer = f"Ассистент сейчас недоступен: {exc}"

    db.add(ChatMessage(session_id=session.id, role="assistant", content=answer))
    session.preview = answer[:240]
    session.updated_at = datetime.now(timezone.utc)
    db.commit()
    return get_session(session.id, user, db)
