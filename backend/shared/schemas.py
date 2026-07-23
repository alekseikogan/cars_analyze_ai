from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class VehicleStatus(str, Enum):
    CREATED = "created"
    SENT_TO_ML = "sent_to_ml"
    ML_PROCESSING = "ml_processing"


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
