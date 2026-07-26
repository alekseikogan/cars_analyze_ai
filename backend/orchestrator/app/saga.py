from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.orchestrator.app.mongo import get_db


@dataclass
class PipelineState:
    enrichment_done: bool = False
    price_done: bool = False
    predicted_price: float | None = None
    confidence: float | None = None


class SagaStore:
    """Saga state persisted in MongoDB (collection: sagas)."""

    collection_name = "sagas"

    @property
    def collection(self):
        return get_db()[self.collection_name]

    async def get_or_create(self, vehicle_id: int) -> PipelineState:
        doc = await self.collection.find_one({"_id": vehicle_id})
        if doc is None:
            state = PipelineState()
            await self.save(vehicle_id, state)
            return state
        return PipelineState(
            enrichment_done=bool(doc.get("enrichment_done", False)),
            price_done=bool(doc.get("price_done", False)),
            predicted_price=doc.get("predicted_price"),
            confidence=doc.get("confidence"),
        )

    async def save(self, vehicle_id: int, state: PipelineState) -> None:
        await self.collection.update_one(
            {"_id": vehicle_id},
            {
                "$set": {
                    "enrichment_done": state.enrichment_done,
                    "price_done": state.price_done,
                    "predicted_price": state.predicted_price,
                    "confidence": state.confidence,
                    "updated_at": datetime.now(timezone.utc),
                }
            },
            upsert=True,
        )

    async def clear(self, vehicle_id: int) -> None:
        await self.collection.delete_one({"_id": vehicle_id})


saga_store = SagaStore()
