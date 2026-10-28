from contextlib import asynccontextmanager
import aio_pika
import os

from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.shared.schemas import VehicleCreate, VehicleRead
from backend.gateway.app.db import get_db, init_db
from backend.gateway.app.models import Vehicle
from backend.gateway.app.publisher import publish_vehicle_created
from backend.shared.events import (
    VEHICLE_CREATED,
    VEHICLE_CREATED_QUEUE,
    VEHICLE_EXCHANGE,
    VehicleCreatedEvent,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables, then connect RabbitMQ and declare the vehicle.created queue."""
    print("Application starting...")
    init_db()

    connection = await aio_pika.connect_robust(os.getenv("RABBITMQ_URL"))
    channel = await connection.channel()
    exchange = await channel.declare_exchange(
        name=VEHICLE_EXCHANGE,
        type=aio_pika.ExchangeType.TOPIC,
    )
    queue = await channel.declare_queue(name=VEHICLE_CREATED_QUEUE)
    await queue.bind(exchange, routing_key=VEHICLE_CREATED)

    app.state.connection = connection
    app.state.channel = channel
    app.state.exchange = exchange
    app.state.queue = queue

    yield

    await connection.close()
    print("Application stopped")


app = FastAPI(title="Gateway", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost",
        "http://127.0.0.1",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/vehicles")
async def create_vehicle(
    vehicle: VehicleCreate,
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    """Save a vehicle and start the enrichment and pricing pipeline."""
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

    create_event = VehicleCreatedEvent(
        vehicle_id=db_vehicle.id,
        brand=db_vehicle.brand,
        model=db_vehicle.model,
        year=db_vehicle.year,
        mileage=db_vehicle.mileage,
        color=db_vehicle.color,
        body_type=db_vehicle.body_type,
    )
    await publish_vehicle_created(create_event, request)

    return {
        "message": "Vehicle created successfully",
        "id": db_vehicle.id,
        "vehicle": vehicle.model_dump(),
    }


@app.get("/vehicles", response_model=list[VehicleRead])
async def get_vehicles(db: Session = Depends(get_db)):
    """Return every saved vehicle."""
    result = db.execute(select(Vehicle))
    return list(result.scalars().all())


@app.get("/vehicles/{vehicle_id}", response_model=VehicleRead)
async def get_vehicle(vehicle_id: int, db: Session = Depends(get_db)):
    """Return one vehicle by id."""
    vehicle = db.get(Vehicle, vehicle_id)
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle
