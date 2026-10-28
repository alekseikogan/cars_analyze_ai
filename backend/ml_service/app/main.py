from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from backend.ml_service.app.predictor import predict
from backend.shared.schemas import PricePredictRequest, PricePredictResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml-service")

app = FastAPI(title="ML Price Service")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the ML service is up."""
    return {"status": "ok"}


@app.post("/predict", response_model=PricePredictResult)
def predict_price(payload: PricePredictRequest) -> PricePredictResult:
    """Estimate a vehicle price from its attributes."""
    try:
        result = predict(payload)
    except Exception as exc:
        logger.exception("predict failed vehicle_id=%s", payload.vehicle_id)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    logger.info(
        "predicted vehicle_id=%s price=%s confidence=%s",
        result.vehicle_id,
        result.predicted_price,
        result.confidence,
    )
    return result
