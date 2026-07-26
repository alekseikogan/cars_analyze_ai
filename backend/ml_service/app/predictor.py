from __future__ import annotations

from datetime import datetime

from backend.shared.schemas import PricePredictRequest, PricePredictResult

# Rough EUR base prices by body type (demo heuristic, not a real model)
_BODY_BASE_EUR: dict[str, float] = {
    "sedan": 14000,
    "hatchback": 11000,
    "wagon": 13000,
    "suv": 18000,
    "coupe": 16000,
    "van": 12000,
    "pickup": 17000,
    "convertible": 15000,
}

_BRAND_FACTOR: dict[str, float] = {
    "bmw": 1.25,
    "mercedes": 1.3,
    "mercedes-benz": 1.3,
    "audi": 1.22,
    "volkswagen": 1.05,
    "vw": 1.05,
    "skoda": 0.95,
    "toyota": 1.1,
    "ford": 0.95,
    "opel": 0.9,
    "renault": 0.88,
    "peugeot": 0.9,
}


def _normalize(value: str | None) -> str:
    return (value or "").strip().lower()


def predict(request: PricePredictRequest) -> PricePredictResult:
    """Heuristic price estimate for the auction demo pipeline."""
    current_year = datetime.now().year
    age = max(current_year - request.year, 0)

    body_key = _normalize(request.body_type)
    brand_key = _normalize(request.brand)

    base = _BODY_BASE_EUR.get(body_key, 12000.0)
    brand_factor = _BRAND_FACTOR.get(brand_key, 1.0)

    # Age: ~7% drop per year, floor at 25% of base
    age_factor = max(0.25, 1.0 - age * 0.07)

    # Mileage: ~0.4% drop per 1000 km, floor at 30%
    mileage_factor = max(0.30, 1.0 - (request.mileage / 1000.0) * 0.004)

    predicted = round(base * brand_factor * age_factor * mileage_factor, 2)

    # Confidence: how "complete"/typical the input looks (0..1)
    confidence = 0.55
    if request.color:
        confidence += 0.1
    if body_key in _BODY_BASE_EUR:
        confidence += 0.1
    if brand_key in _BRAND_FACTOR:
        confidence += 0.1
    if 0 < request.mileage < 300_000:
        confidence += 0.1
    confidence = min(round(confidence, 2), 0.95)

    return PricePredictResult(
        vehicle_id=request.vehicle_id,
        predicted_price=predicted,
        confidence=confidence,
    )
