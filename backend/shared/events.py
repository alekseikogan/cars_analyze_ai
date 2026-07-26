from pydantic import BaseModel, Field
from backend.shared.schemas import VehicleCreate

VEHICLE_CREATED = "vehicle.created"

class VehicleCreatedEvent(BaseModel):   
    vehicle_id: int
    event_type: str = VEHICLE_CREATED
    brand: str
    model: str
    year: int 
    mileage: int 
    color: str | None = None
    body_type: str
