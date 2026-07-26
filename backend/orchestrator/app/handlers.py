from __future__ import annotations

import logging
import os

import httpx
from aio_pika.abc import AbstractExchange

from backend.gateway.app.db import SessionLocal
from backend.gateway.app.models import Vehicle
from backend.orchestrator.app.publisher import publish_event
from backend.orchestrator.app.saga import saga_store
from backend.shared.events import (
    VEHICLE_PRICE_REQUESTED,
    VEHICLE_PROCESSING_COMPLETED,
    VehicleCreatedEvent,
    VehiclePriceCompletedEvent,
    VehiclePriceRequestedEvent,
    VehicleProcessingCompletedEvent,
)
from backend.shared.schemas import EnrichmentResult, VehicleStatus

logger = logging.getLogger(__name__)


def _set_status(vehicle_id: int, status: VehicleStatus) -> None:
    db = SessionLocal()
    try:
        vehicle = db.get(Vehicle, vehicle_id)
        if vehicle is None:
            raise ValueError(f"Vehicle {vehicle_id} not found")
        vehicle.status = status
        db.commit()
    finally:
        db.close()


def _run_enrichment(event: VehicleCreatedEvent) -> EnrichmentResult:
    base_url = os.getenv("ENRICHMENT_URL", "http://127.0.0.1:8002").rstrip("/")
    payload = {
        "vehicle_id": event.vehicle_id,
        "brand": event.brand,
        "model": event.model,
        "year": event.year,
        "mileage": event.mileage,
        "color": event.color,
        "body_type": event.body_type,
    }
    logger.info("enrichment: calling %s/enrich vehicle_id=%s", base_url, event.vehicle_id)
    with httpx.Client(timeout=60.0) as client:
        response = client.post(f"{base_url}/enrich", json=payload)
        response.raise_for_status()
    result = EnrichmentResult.model_validate(response.json())
    logger.info(
        "enrichment done vehicle_id=%s segment=%s",
        result.vehicle_id,
        result.market_segment,
    )
    return result


async def _try_finish(vehicle_id: int, exchange: AbstractExchange) -> None:
    state = saga_store.get_or_create(vehicle_id)
    if not (state.enrichment_done and state.price_done):
        logger.info(
            "saga waiting vehicle_id=%s enrichment=%s price=%s",
            vehicle_id,
            state.enrichment_done,
            state.price_done,
        )
        return

    _set_status(vehicle_id, VehicleStatus.READY)
    await publish_event(
        exchange,
        VEHICLE_PROCESSING_COMPLETED,
        VehicleProcessingCompletedEvent(
            vehicle_id=vehicle_id,
            predicted_price=state.predicted_price,
            confidence=state.confidence,
        ),
    )
    saga_store.clear(vehicle_id)
    logger.info("orchestrator finished vehicle_id=%s status=ready", vehicle_id)


async def process_vehicle_created(
    event: VehicleCreatedEvent,
    exchange: AbstractExchange,
) -> None:
    """Start saga: enrichment (HTTP for now) + request market price via event."""
    logger.info("orchestrator received vehicle.created: %s", event.model_dump())
    state = saga_store.get_or_create(event.vehicle_id)

    _set_status(event.vehicle_id, VehicleStatus.PROCESSING)

    try:
        _run_enrichment(event)
        state.enrichment_done = True

        price_request = VehiclePriceRequestedEvent(
            vehicle_id=event.vehicle_id,
            brand=event.brand,
            model=event.model,
            year=event.year,
            mileage=event.mileage,
            color=event.color,
            body_type=event.body_type,
        )
        await publish_event(exchange, VEHICLE_PRICE_REQUESTED, price_request)
        # READY only after vehicle.price.completed (see process_price_completed)
    except Exception:
        logger.exception("orchestrator failed vehicle_id=%s", event.vehicle_id)
        try:
            _set_status(event.vehicle_id, VehicleStatus.FAILED)
        except Exception:
            logger.exception("failed to mark vehicle_id=%s as failed", event.vehicle_id)
        saga_store.clear(event.vehicle_id)
        raise


async def process_price_completed(
    event: VehiclePriceCompletedEvent,
    exchange: AbstractExchange,
) -> None:
    logger.info(
        "orchestrator received price.completed vehicle_id=%s price=%s confidence=%s",
        event.vehicle_id,
        event.predicted_price,
        event.confidence,
    )
    state = saga_store.get_or_create(event.vehicle_id)
    state.price_done = True
    state.predicted_price = event.predicted_price
    state.confidence = event.confidence
    await _try_finish(event.vehicle_id, exchange)
