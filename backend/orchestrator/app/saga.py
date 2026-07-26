from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PipelineState:
    enrichment_done: bool = False
    price_done: bool = False
    predicted_price: float | None = None
    confidence: float | None = None


@dataclass
class SagaStore:
    """In-memory saga state (later can move to MongoDB)."""

    _items: dict[int, PipelineState] = field(default_factory=dict)

    def get_or_create(self, vehicle_id: int) -> PipelineState:
        if vehicle_id not in self._items:
            self._items[vehicle_id] = PipelineState()
        return self._items[vehicle_id]

    def clear(self, vehicle_id: int) -> None:
        self._items.pop(vehicle_id, None)


saga_store = SagaStore()
