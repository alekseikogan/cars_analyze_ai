from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from backend.orchestrator.app.mongo import get_db


@dataclass
class PipelineState:
    enrichment_done: bool = False
    price_requested: bool = False
    price_done: bool = False
    predicted_price: float | None = None
    confidence: float | None = None
    enrichment: dict | None = None
    status: str = "running"  # running | completed | failed | compensated
    compensations: list[str] = field(default_factory=list)
    error: str | None = None


class SagaStore:
    """Активная сага в `sagas`; завершённые и упавшие копии уходят в `saga_history`."""

    active_collection = "sagas"
    history_collection = "saga_history"

    @property
    def collection(self):
        """Возвращает коллекцию ещё идущих саг."""
        return get_db()[self.active_collection]

    @property
    def history(self):
        """Возвращает коллекцию завершённых и упавших саг."""
        return get_db()[self.history_collection]

    def _to_state(self, doc: dict) -> PipelineState:
        """Собирает состояние пайплайна из документа Mongo."""
        return PipelineState(
            enrichment_done=bool(doc.get("enrichment_done", False)),
            price_requested=bool(doc.get("price_requested", False)),
            price_done=bool(doc.get("price_done", False)),
            predicted_price=doc.get("predicted_price"),
            confidence=doc.get("confidence"),
            enrichment=doc.get("enrichment"),
            status=doc.get("status", "running"),
            compensations=list(doc.get("compensations") or []),
            error=doc.get("error"),
        )

    async def get(self, vehicle_id: int) -> PipelineState | None:
        """Загружает активную сагу авто, если она есть."""
        doc = await self.collection.find_one({"_id": vehicle_id})
        if doc is None:
            return None
        return self._to_state(doc)

    async def get_or_create(self, vehicle_id: int) -> PipelineState:
        """Загружает активную сагу или создаёт новую для этого авто."""
        state = await self.get(vehicle_id)
        if state is None:
            state = PipelineState()
            await self.save(vehicle_id, state)
        return state

    async def save(self, vehicle_id: int, state: PipelineState) -> None:
        """Сохраняет или обновляет состояние активной саги."""
        payload = asdict(state)
        payload["updated_at"] = datetime.now(timezone.utc)
        await self.collection.update_one(
            {"_id": vehicle_id},
            {"$set": payload},
            upsert=True,
        )

    async def archive(
        self,
        vehicle_id: int,
        *,
        final_status: str,
        error: str | None = None,
        compensations: list[str] | None = None,
    ) -> None:
        """Переносит активную сагу в saga_history, историю не удаляет."""
        doc = await self.collection.find_one({"_id": vehicle_id})
        now = datetime.now(timezone.utc)
        if doc is None:
            history_doc = {
                "vehicle_id": vehicle_id,
                "final_status": final_status,
                "error": error,
                "compensations": compensations or [],
                "archived_at": now,
            }
        else:
            history_doc = {k: v for k, v in doc.items() if k != "_id"}
            history_doc["vehicle_id"] = vehicle_id
            history_doc["final_status"] = final_status
            if error is not None:
                history_doc["error"] = error
            if compensations is not None:
                history_doc["compensations"] = compensations
            history_doc["archived_at"] = now

        await self.history.insert_one(history_doc)
        await self.collection.delete_one({"_id": vehicle_id})


saga_store = SagaStore()
