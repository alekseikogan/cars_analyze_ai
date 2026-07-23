from fastapi import FastAPI
from backend.shared.schemas import VehicleCreate


app = FastAPI(title="Gateway")
data: list[VehicleCreate] = []

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/vehicles")
def create_vehicle(vehicle: VehicleCreate):
    data.append(vehicle)
    return {
        "message": "Vehicle created successfully",
        "vehicle": vehicle.model_dump()
        }


@app.get(
    "/vehicles",
    response_model=list[VehicleCreate]
    )
def get_vehicles():
    return data