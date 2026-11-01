from __future__ import annotations

from typing import Annotated

from langchain_core.messages import AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

from backend.assistant.app.tools import MANAGER_TOOLS, READ_TOOLS
from backend.enrichment.app.config import get_openai_api_key, get_openai_model

SYSTEM_PROMPT = """
You are the staff assistant of a car auction.
The employee role is: {role}.
- support: answer questions about cars, prices and statuses. You cannot reserve listings.
- auction_manager: same access, and you may reserve a listing only when the manager clearly asks to reserve a specific listing_id.

Answer in Russian, in plain text without markdown.
Take prices, mileage, status and equipment only from tool results. Never invent numbers.
If a tool returns nothing, say that the catalog has no such car.
Keep the answer short and name listing_id when you talk about a specific lot.
""".strip()


class ChatState(TypedDict):
    """Состояние графа: история сообщений сессии и роль сотрудника."""

    messages: Annotated[list, add_messages]
    role: str


def _answer_text(message: AIMessage) -> str:
    """Достаёт текст из ответа модели, если он пришёл строкой или списком блоков."""
    content = message.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text") or ""))
        return "\n".join(part for part in parts if part).strip()
    return str(content or "").strip()


def build_graph(role: str):
    """Собирает граф: agent решает, tools выполняет, условие смотрит на tool_calls."""
    tools = MANAGER_TOOLS if role == "auction_manager" else READ_TOOLS
    llm = ChatOpenAI(
        model=get_openai_model(),
        api_key=get_openai_api_key(),
        temperature=0.2,
    ).bind_tools(tools)

    def agent(state: ChatState) -> dict:
        """Вершина agent: модель отвечает или просит инструмент."""
        system = SystemMessage(content=SYSTEM_PROMPT.format(role=state.get("role") or role))
        response = llm.invoke([system, *state["messages"]])
        return {"messages": [response]}

    graph = StateGraph(ChatState)
    graph.add_node("agent", agent)
    graph.add_node("tools", ToolNode(tools))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", tools_condition)
    graph.add_edge("tools", "agent")
    return graph.compile()


def run_chat(role: str, messages: list) -> str:
    """Прогоняет историю сессии через граф и возвращает текст ответа."""
    graph = build_graph(role)
    result = graph.invoke(
        {"messages": messages, "role": role},
        {"recursion_limit": 12},
    )
    for message in reversed(result["messages"]):
        if isinstance(message, AIMessage) and not message.tool_calls:
            text = _answer_text(message)
            if text:
                return text
    return "Не удалось собрать ответ. Спросите ещё раз чуть конкретнее."
