from __future__ import annotations

import logging

import aio_pika
from aio_pika.abc import AbstractExchange

from backend.shared.events import (
    VEHICLE_PRICE_COMPLETED,
    VehiclePriceCompletedEvent,
)

logger = logging.getLogger(__name__)


async def publish_price_completed(
    exchange: AbstractExchange,
    event: VehiclePriceCompletedEvent,
) -> None:
    """Publish vehicle.price.completed with the estimate."""
    message = aio_pika.Message(
        body=event.model_dump_json().encode("utf-8"),
        content_type="application/json",
    )
    await exchange.publish(message, routing_key=VEHICLE_PRICE_COMPLETED)
    logger.info(
        "published %s vehicle_id=%s price=%s",
        VEHICLE_PRICE_COMPLETED,
        event.vehicle_id,
        event.predicted_price,
    )
