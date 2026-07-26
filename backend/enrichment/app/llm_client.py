from __future__ import annotations

import json
import logging

from openai import OpenAI

from backend.enrichment.app.config import get_openai_api_key, get_openai_model
from backend.shared.schemas import EnrichmentRequest, EnrichmentResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You enrich used-car listings for an auction platform.
Return ONLY valid JSON with these keys:
- likely_trim: string or null (e.g. "Ambition", "Sportline")
- likely_options: array of strings (typical options for this car)
- condition_notes: short string about expected wear given year/mileage
- market_segment: one of "budget", "mainstream", "premium", "luxury"
- summary: 1-2 sentences for auction managers
""".strip()


def enrich_vehicle(payload: EnrichmentRequest) -> EnrichmentResult:
    client = OpenAI(api_key=get_openai_api_key())
    model = get_openai_model()

    user_prompt = (
        "Enrich this vehicle:\n"
        f"- id: {payload.vehicle_id}\n"
        f"- brand: {payload.brand}\n"
        f"- model: {payload.model}\n"
        f"- year: {payload.year}\n"
        f"- mileage: {payload.mileage}\n"
        f"- color: {payload.color}\n"
        f"- body_type: {payload.body_type}\n"
    )

    logger.info(
        "Calling OpenAI model=%s vehicle_id=%s",
        model,
        payload.vehicle_id,
    )

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )

    content = response.choices[0].message.content or "{}"
    data = json.loads(content)

    return EnrichmentResult(
        vehicle_id=payload.vehicle_id,
        likely_trim=data.get("likely_trim"),
        likely_options=data.get("likely_options") or [],
        condition_notes=data.get("condition_notes"),
        market_segment=data.get("market_segment"),
        summary=data.get("summary"),
        raw_model=model,
    )
