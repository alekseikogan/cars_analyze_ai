from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class VehicleStatus(str, Enum):
    CREATED = "created"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VehicleCreate(BaseModel):
    brand: str
    model: str
    year: int = Field(..., gt=1900, le=2026)
    mileage: int = Field(..., ge=0)
    color: str | None = None
    body_type: str


class VehicleRead(VehicleCreate):
    id: int
    created_at: datetime
    status: VehicleStatus

    model_config = {
        "from_attributes": True,
    }


class EnrichmentRequest(BaseModel):
    vehicle_id: int
    brand: str
    model: str
    year: int
    mileage: int
    color: str | None = None
    body_type: str


class EnrichmentResult(BaseModel):
    vehicle_id: int
    likely_trim: str | None = None
    likely_options: list[str] = Field(default_factory=list)
    condition_notes: str | None = None
    market_segment: str | None = None
    summary: str | None = None
    raw_model: str | None = None
