from __future__ import annotations

import logging
import os

import httpx

from backend.gateway.app.db import SessionLocal
from backend.gateway.app.models import Vehicle
from backend.shared.events import VehicleCreatedEvent
from backend.shared.schemas import EnrichmentResult, PricePredictResult, VehicleStatus

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
        "enrichment done vehicle_id=%s segment=%s options=%s",
        result.vehicle_id,
        result.market_segment,
        result.likely_options,
    )
    return result


def _run_market_price(event: VehicleCreatedEvent) -> None:
    # Reserved for a dedicated market-price consumer later
    logger.info("market-price: skip for now vehicle_id=%s", event.vehicle_id)


def _run_ml(event: VehicleCreatedEvent) -> PricePredictResult:
    base_url = os.getenv("ML_SERVICE_URL", "http://127.0.0.1:8001").rstrip("/")
    payload = {
        "vehicle_id": event.vehicle_id,
        "brand": event.brand,
        "model": event.model,
        "year": event.year,
        "mileage": event.mileage,
        "color": event.color,
        "body_type": event.body_type,
    }
    logger.info("ml-service: calling %s/predict vehicle_id=%s", base_url, event.vehicle_id)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{base_url}/predict", json=payload)
        response.raise_for_status()
    result = PricePredictResult.model_validate(response.json())
    logger.info(
        "ml-service done vehicle_id=%s price=%s confidence=%s",
        result.vehicle_id,
        result.predicted_price,
        result.confidence,
    )
    return result


def process_vehicle_created(event: VehicleCreatedEvent) -> None:
    """Pipeline after vehicle.created: processing → steps → ready|failed."""
    logger.info("orchestrator received vehicle.created: %s", event.model_dump())

    _set_status(event.vehicle_id, VehicleStatus.PROCESSING)

    try:
        _run_enrichment(event)
        _run_market_price(event)
        _run_ml(event)
        _set_status(event.vehicle_id, VehicleStatus.READY)
        logger.info("orchestrator finished vehicle_id=%s status=ready", event.vehicle_id)
    except Exception:
        logger.exception("orchestrator failed vehicle_id=%s", event.vehicle_id)
        try:
            _set_status(event.vehicle_id, VehicleStatus.FAILED)
        except Exception:
            logger.exception("failed to mark vehicle_id=%s as failed", event.vehicle_id)
        raise
