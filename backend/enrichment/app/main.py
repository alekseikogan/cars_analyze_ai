from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException

from backend.enrichment.app.llm_client import enrich_vehicle
from backend.shared.schemas import EnrichmentRequest, EnrichmentResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("enrichment")

app = FastAPI(title="Enrichment Service")


@app.get("/health")
def health() -> dict[str, str]:
    """Report that the enrichment service is up."""
    return {"status": "ok"}


@app.post("/enrich", response_model=EnrichmentResult)
def enrich(payload: EnrichmentRequest) -> EnrichmentResult:
    """Enrich a vehicle listing through the LLM and return structured fields."""
    try:
        result = enrich_vehicle(payload)
    except RuntimeError as exc:
        # missing API key, etc.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("enrichment failed vehicle_id=%s", payload.vehicle_id)
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI enrichment failed: {exc}",
        ) from exc

    logger.info("enriched vehicle_id=%s segment=%s", result.vehicle_id, result.market_segment)
    return result
