from __future__ import annotations

import logging

from aio_pika.abc import AbstractExchange

from backend.market_price.app.ml_client import predict_price
from backend.market_price.app.publisher import publish_price_completed
from backend.shared.events import (
    VehiclePriceCompletedEvent,
    VehiclePriceRequestedEvent,
)

logger = logging.getLogger(__name__)


async def process_price_requested(
    event: VehiclePriceRequestedEvent,
    exchange: AbstractExchange,
) -> None:
    """Estimate the price and publish vehicle.price.completed."""
    logger.info("market-price received request: %s", event.model_dump())
    result = predict_price(event)
    completed = VehiclePriceCompletedEvent(
        vehicle_id=result.vehicle_id,
        predicted_price=result.predicted_price,
        confidence=result.confidence,
    )
    await publish_price_completed(exchange, completed)
