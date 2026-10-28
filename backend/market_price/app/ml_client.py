from __future__ import annotations

import logging
import os

import httpx

from backend.shared.events import VehiclePriceRequestedEvent
from backend.shared.schemas import PricePredictResult

logger = logging.getLogger(__name__)


def predict_price(event: VehiclePriceRequestedEvent) -> PricePredictResult:
    """Call the ML service and return the price estimate."""
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
    logger.info("Calling ML %s/predict vehicle_id=%s", base_url, event.vehicle_id)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(f"{base_url}/predict", json=payload)
        response.raise_for_status()
    return PricePredictResult.model_validate(response.json())
