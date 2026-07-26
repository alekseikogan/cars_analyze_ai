from fastapi import FastAPI, Depends, Session
from backend.shared.schemas import VehicleCreate, VehicleRead
from backend.gateway.app.db import get_db, init_db
from backend.gateway.app.models import Vehicle
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Application starting...")
    init_db()
    yield
    print("Application stopped")


app = FastAPI(title="Gateway", lifespan=lifespan)


@app.post("/vehicles")
def create_vehicle(vehicle: VehicleCreate, db: Session = Depends(get_db)):
    db_vehicle = Vehicle(
        brand=vehicle.brand,
        model=vehicle.model,
        year=vehicle.year,
        mileage=vehicle.mileage,
        color=vehicle.color,
        body_type=vehicle.body_type,
    )
    db.add(db_vehicle)
    db.commit()
    db.refresh(db_vehicle)
    return {
        "message": "Vehicle created successfully",
        "vehicle": vehicle.model_dump()
        }


@app.get(
    "/vehicles",
    response_model=list[VehicleCreate]
    )
def get_vehicles(db: Session = Depends(get_db)):
    query = select(Vehicle)
    result = db.execute(query)
    return result.scalars().all()
