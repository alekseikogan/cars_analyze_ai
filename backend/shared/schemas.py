from pydantic import BaseModel, Field

class VehicleCreate(BaseModel):
    brand: str
    model: str
    year: int = Field(..., gt=1900, lt=2026)
    mileage: int = Field(..., gt=0)
    color: str
    body_type: str
