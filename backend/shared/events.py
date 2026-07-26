from pydantic import BaseModel, Field

VEHICLE_EXCHANGE = "vehicle"

VEHICLE_CREATED = "vehicle.created"
VEHICLE_CREATED_QUEUE = "vehicle.created"

VEHICLE_PRICE_REQUESTED = "vehicle.price.requested"
VEHICLE_PRICE_REQUESTED_QUEUE = "vehicle.price.requested"

VEHICLE_PRICE_COMPLETED = "vehicle.price.completed"
VEHICLE_PRICE_COMPLETED_QUEUE = "vehicle.price.completed"

VEHICLE_PROCESSING_COMPLETED = "vehicle.processing.completed"
VEHICLE_PROCESSING_COMPLETED_QUEUE = "vehicle.processing.completed"


class VehicleCreatedEvent(BaseModel):
    vehicle_id: int
    event_type: str = VEHICLE_CREATED
    brand: str
    model: str
    year: int
    mileage: int
    color: str | None = None
    body_type: str


class VehiclePriceRequestedEvent(BaseModel):
    vehicle_id: int
    event_type: str = VEHICLE_PRICE_REQUESTED
    brand: str
    model: str
    year: int
    mileage: int
    color: str | None = None
    body_type: str


class VehiclePriceCompletedEvent(BaseModel):
    vehicle_id: int
    event_type: str = VEHICLE_PRICE_COMPLETED
    predicted_price: float
    confidence: float = Field(..., ge=0, le=1)


class VehicleProcessingCompletedEvent(BaseModel):
    vehicle_id: int
    event_type: str = VEHICLE_PROCESSING_COMPLETED
    predicted_price: float | None = None
    confidence: float | None = None
