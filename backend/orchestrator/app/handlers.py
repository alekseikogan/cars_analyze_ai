from __future__ import annotations

import logging

from backend.gateway.app.db import SessionLocal
from backend.gateway.app.models import Vehicle
from backend.shared.events import VehicleCreatedEvent
from backend.shared.schemas import VehicleStatus

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


def _run_enrichment(event: VehicleCreatedEvent) -> None:
    # TODO: HTTP/call to backend.enrichment
    logger.info("enrichment: vehicle_id=%s brand=%s model=%s", event.vehicle_id, event.brand, event.model)


def _run_market_price(event: VehicleCreatedEvent) -> None:
    # TODO: HTTP/call to backend.market-price
    logger.info("market-price: vehicle_id=%s year=%s mileage=%s", event.vehicle_id, event.year, event.mileage)


def _run_ml(event: VehicleCreatedEvent) -> None:
    # TODO: HTTP/call to backend.ml-service
    logger.info("ml-service: vehicle_id=%s body_type=%s", event.vehicle_id, event.body_type)


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
