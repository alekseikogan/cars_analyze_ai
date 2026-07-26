from pydantic import BaseModel

VEHICLE_EXCHANGE = "vehicle"
VEHICLE_CREATED = "vehicle.created"
VEHICLE_CREATED_QUEUE = "vehicle.created"


class VehicleCreatedEvent(BaseModel):
    vehicle_id: int
    event_type: str = VEHICLE_CREATED
    brand: str
    model: str
    year: int
    mileage: int
    color: str | None = None
    body_type: str
