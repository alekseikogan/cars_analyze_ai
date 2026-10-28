from __future__ import annotations

import logging
import os

import httpx
from aio_pika.abc import AbstractExchange

from backend.gateway.app.db import SessionLocal
from backend.gateway.app.models import Vehicle
from backend.orchestrator.app.publisher import publish_event
from backend.orchestrator.app.saga import PipelineState, saga_store
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
    """Write the vehicle processing status in Postgres."""
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
    """Call the enrichment service and return the LLM description of the vehicle."""
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


async def _compensate(vehicle_id: int, state: PipelineState, error: str) -> None:
    """Rollback completed saga steps (best-effort) and archive as compensated."""
    had_price = state.price_done
    had_price_request = state.price_requested
    had_enrichment = state.enrichment_done
    actions: list[str] = []

    if had_price:
        actions.append("void_price_result")
        state.price_done = False
        state.predicted_price = None
        state.confidence = None
        logger.warning("compensate vehicle_id=%s: void price result", vehicle_id)

    if had_price_request and not had_price:
        actions.append("cancel_pending_price_request")
        state.price_requested = False
        logger.warning(
            "compensate vehicle_id=%s: ignore/cancel pending price request",
            vehicle_id,
        )

    if had_enrichment:
        actions.append("void_enrichment_result")
        state.enrichment_done = False
        state.enrichment = None
        logger.warning("compensate vehicle_id=%s: void enrichment result", vehicle_id)

    actions.append("set_vehicle_status_failed")
    state.status = "compensated"
    state.compensations = actions
    state.error = error
    await saga_store.save(vehicle_id, state)

    try:
        _set_status(vehicle_id, VehicleStatus.FAILED)
    except Exception:
        logger.exception("compensate: failed to set FAILED for vehicle_id=%s", vehicle_id)

    await saga_store.archive(
        vehicle_id,
        final_status="compensated",
        error=error,
        compensations=actions,
    )
    logger.info(
        "saga compensated vehicle_id=%s actions=%s error=%s",
        vehicle_id,
        actions,
        error,
    )


async def _try_finish(vehicle_id: int, exchange: AbstractExchange) -> None:
    """Mark the vehicle ready and publish processing-completed once both steps are done."""
    state = await saga_store.get_or_create(vehicle_id)
    if state.status in {"compensated", "failed"}:
        logger.info("skip finish for terminal saga vehicle_id=%s", vehicle_id)
        return

    if not (state.enrichment_done and state.price_done):
        logger.info(
            "saga waiting vehicle_id=%s enrichment=%s price=%s",
            vehicle_id,
            state.enrichment_done,
            state.price_done,
        )
        return

    try:
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
        state.status = "completed"
        await saga_store.save(vehicle_id, state)
        await saga_store.archive(vehicle_id, final_status="completed")
        logger.info("orchestrator finished vehicle_id=%s status=ready", vehicle_id)
    except Exception as exc:
        logger.exception("finish failed vehicle_id=%s — compensating", vehicle_id)
        await _compensate(vehicle_id, state, error=str(exc))
        raise


async def process_vehicle_created(
    event: VehicleCreatedEvent,
    exchange: AbstractExchange,
) -> None:
    """Start saga: enrichment + request market price via event."""
    logger.info("orchestrator received vehicle.created: %s", event.model_dump())
    state = await saga_store.get_or_create(event.vehicle_id)

    _set_status(event.vehicle_id, VehicleStatus.PROCESSING)

    try:
        enrichment = _run_enrichment(event)
        state.enrichment_done = True
        state.enrichment = enrichment.model_dump()
        await saga_store.save(event.vehicle_id, state)

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
        state.price_requested = True
        await saga_store.save(event.vehicle_id, state)
    except Exception as exc:
        logger.exception("orchestrator failed vehicle_id=%s", event.vehicle_id)
        await _compensate(event.vehicle_id, state, error=str(exc))
        raise


async def process_price_completed(
    event: VehiclePriceCompletedEvent,
    exchange: AbstractExchange,
) -> None:
    """Store the price estimate and finish the saga when enrichment is also done."""
    logger.info(
        "orchestrator received price.completed vehicle_id=%s price=%s confidence=%s",
        event.vehicle_id,
        event.predicted_price,
        event.confidence,
    )
    state = await saga_store.get(event.vehicle_id)
    if state is None or state.status in {"compensated", "failed", "completed"}:
        logger.warning(
            "ignore price.completed for inactive saga vehicle_id=%s status=%s",
            event.vehicle_id,
            None if state is None else state.status,
        )
        return

    try:
        state.price_done = True
        state.predicted_price = event.predicted_price
        state.confidence = event.confidence
        await saga_store.save(event.vehicle_id, state)
        await _try_finish(event.vehicle_id, exchange)
    except Exception as exc:
        logger.exception("price.completed handling failed vehicle_id=%s", event.vehicle_id)
        fresh = await saga_store.get(event.vehicle_id)
        if fresh is not None and fresh.status == "running":
            await _compensate(event.vehicle_id, fresh, error=str(exc))
        raise
