from __future__ import annotations

import logging
import os
import sys
from collections import deque
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Deque, Dict, List, Optional, Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Header, Depends
from pydantic import BaseModel, Field

# --- Path Setup ---
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# --- Optional Library Imports ---
try:
    from libs.mailer.client import EmailClient, EmailConfig
except Exception:
    EmailClient = None
    EmailConfig = None

try:
    from libs.mongo.storage import MongoConfig, MongoStorage
except Exception as exc:
    MongoConfig = None
    MongoStorage = None

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Plantbox API", version="0.2.0")

# --- Default/Fallback Data ---
DEFAULT_TARGETS = {
    "air_temp": {"min": 18.0, "max": 28.0},
    "humidity": {"min": 40.0, "max": 80.0},
    "water_level": {"min": 50.0, "max": 100.0},
}

# --- Pydantic Models (Updated for "My Basil" UI) ---

class LightSchedule(BaseModel):
    start: time
    end: time

class TargetRange(BaseModel):
    min: float
    max: float

class DeviceCamera(BaseModel):
    stream_url: Optional[str] = None
    snapshot_url: Optional[str] = None
    enabled: bool = False

# Replaces the old ConfigState to match the new UI/DB schema
class DeviceConfig(BaseModel):
    hardware_id: str
    display_name: str = "My PlantBox"
    owner_id: str
    
    # Schedules shown in the UI
    light_schedule: LightSchedule
    
    # Thresholds (Used to determine if UI card is Green or Red)
    targets: Dict[str, TargetRange] = {
        "air_temp": TargetRange(**DEFAULT_TARGETS["air_temp"]),
        "humidity": TargetRange(**DEFAULT_TARGETS["humidity"]),
        "water_level": TargetRange(**DEFAULT_TARGETS["water_level"])
    }
    
    camera: DeviceCamera = DeviceCamera()
    
    # Heartbeat tracking
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_online: bool = True
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SensorReadings(BaseModel):
    air_temp_c: float = Field(..., description="Air Temperature in Celsius")
    humidity_pct: float = Field(..., ge=0, le=100, description="Relative Humidity %")
    light_intensity_pct: float = Field(..., ge=0, le=100)
    water_level_pct: float = Field(..., ge=0, le=100)
    nutrient_a_pct: float = Field(..., ge=0, le=100, description="Nutrient Tank A Level")

# class TelemetryIn(BaseModel):
#     device_id: str
#     sensors: SensorReadings
#     captured_at: datetime = Field(default_factory=datetime.utcnow)

class TelemetryIn(BaseModel):
    temperature: float
    heater: float
    fan: float
    watering: float


class TelemetryRecord(TelemetryIn):
    received_at: datetime
    metadata: Dict[str, Any] = {} # For profile_active, etc.

class Notification(BaseModel):
    id: str
    level: str
    message: str
    created_at: datetime
    device_id: str

# --- Helper Functions ---

def model_to_dict(model: BaseModel) -> Dict[str, object]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()

def load_email_settings() -> Optional[Dict[str, object]]:
    if EmailClient is None or EmailConfig is None:
        return None
    smtp_server = os.getenv("SMTP_SERVER")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM")
    recipients_raw = os.getenv("ALERT_RECIPIENTS", "")
    recipients = [item.strip() for item in recipients_raw.split(",") if item.strip()]
    if not smtp_server or not username or not password or not from_email or not recipients:
        return None
    config = EmailConfig(
        smtp_server=smtp_server,
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        username=username,
        password=password,
        use_tls=os.getenv("SMTP_USE_TLS", "true").lower() != "false",
    )
    return {"client": EmailClient(config), "from_email": from_email, "to": recipients}

def build_mongo_storage() -> Optional[MongoStorage]:
    if MongoStorage is None or MongoConfig is None:
        return None
    uri = os.getenv("MONGO_URI")
    if not uri:
        return None
    db_name = os.getenv("MONGO_DB", "plantbox")
    try:
        storage = MongoStorage(MongoConfig(uri=uri, db_name=db_name))
        # Create indexes for performance
        storage.db["telemetry"].create_index([("device_id", 1), ("received_at", -1)])
        storage.db["devices"].create_index([("hardware_id", 1)], unique=True)
        logging.info("Connected to Mongo")
        return storage
    except Exception as exc:
        logging.warning("Mongo disabled/failed: %s", exc)
        return None

# --- Logic: Storage & Notifications ---

def get_or_create_device_config(hardware_id: str) -> DeviceConfig:
    """Loads config from DB or returns default."""
    if MONGO_STORAGE:
        data = MONGO_STORAGE.db["devices"].find_one({"hardware_id": hardware_id})
        if data:
            data.pop("_id", None)
            return DeviceConfig(**data)
            
    # Default Fallback
    return DeviceConfig(
        hardware_id=hardware_id, 
        owner_id="default_user",
        light_schedule=LightSchedule(start=time(6,0), end=time(18,0))
    )

def save_device_config(config: DeviceConfig):
    if MONGO_STORAGE:
        data = model_to_dict(config)
        MONGO_STORAGE.db["devices"].update_one(
            {"hardware_id": config.hardware_id},
            {"$set": data},
            upsert=True
        )

def store_telemetry(record: TelemetryRecord):
    if MONGO_STORAGE:
        MONGO_STORAGE.insert_one("telemetry", model_to_dict(record))

def check_alerts(telemetry: TelemetryIn, config: DeviceConfig) -> List[str]:
    alerts = []
    # sensors = telemetry.sensors
    # targets = config.targets

    # # Check Air Temp
    # if "air_temp" in targets:
    #     t = targets["air_temp"]
    #     if sensors.air_temp_c < t.min or sensors.air_temp_c > t.max:
    #         alerts.append(f"Temp {sensors.air_temp_c}°C out of range ({t.min}-{t.max})")

    # # Check Humidity
    # if "humidity" in targets:
    #     h = targets["humidity"]
    #     if sensors.humidity_pct < h.min or sensors.humidity_pct > h.max:
    #         alerts.append(f"Humidity {sensors.humidity_pct}% out of range")

    # # Check Water
    # if "water_level" in targets:
    #     w = targets["water_level"]
    #     if sensors.water_level_pct < w.min: 
    #          alerts.append(f"Water level low: {sensors.water_level_pct}%")

    return alerts

def queue_notification(level: str, message: str, device_id: str):
    note = Notification(
        id=str(uuid4()),
        level=level,
        message=message,
        created_at=datetime.utcnow(),
        device_id=device_id
    )
    notifications.append(note)
    # Persist notification
    if MONGO_STORAGE:
        MONGO_STORAGE.insert_one("notifications", model_to_dict(note))

    if EMAIL_SETTINGS:
        try:
            EMAIL_SETTINGS["client"].send_email(
                subject=f"Plantbox Alert: {level.upper()}",
                body=f"Device: {device_id}\n\n{message}",
                from_email=EMAIL_SETTINGS["from_email"],
                to_emails=EMAIL_SETTINGS["to"],
            )
        except Exception as exc:
            logging.warning("Email send failed: %s", exc)

# --- Global State (Memory Cache) ---
telemetry_log: Deque[TelemetryRecord] = deque(maxlen=500)
notifications: Deque[Notification] = deque(maxlen=200)
EMAIL_SETTINGS = load_email_settings()
MONGO_STORAGE = build_mongo_storage()

# --- API Endpoints ---

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"targetTemp": 26.5, "triggerWatering": False}

@app.get("/devices/{hardware_id}/config", response_model=DeviceConfig)
def get_device_config(hardware_id: str):
    config = get_or_create_device_config(hardware_id)
    
    # Calculate online status dynamically
    time_diff = datetime.utcnow() - config.last_seen
    config.is_online = time_diff < timedelta(minutes=2)
    
    return config

@app.post("/devices/{hardware_id}/config", response_model=DeviceConfig)
def update_device_config(hardware_id: str, config_update: DeviceConfig):
    if config_update.hardware_id != hardware_id:
        raise HTTPException(status_code=400, detail="Hardware ID mismatch")
    
    config_update.updated_at = datetime.utcnow()
    save_device_config(config_update)
    return config_update

@app.post("/setTelemetry")
def post_telemetry(telemetry: TelemetryIn) -> Dict[str, Any]:
    # 1. Update Device "Last Seen" and Status
    # if MONGO_STORAGE:
    #     MONGO_STORAGE.db["devices"].update_one(
    #         {"hardware_id": telemetry.device_id},
    #         {"$set": {"last_seen": datetime.utcnow(), "is_online": True}}
    #     )

    # # 2. Store Telemetry
    # record = TelemetryRecord(
    #     **model_to_dict(telemetry),
    #     received_at=datetime.utcnow(),
    #     metadata={"processed_by": "plantbox-v2"}
    # )
    # telemetry_log.append(record)
    # store_telemetry(record)

    # # 3. Check Alerts against current config
    # config = get_or_create_device_config(telemetry.device_id)
    # alerts = check_alerts(telemetry, config)
    
    # if alerts:
    #     queue_notification("warning", "; ".join(alerts), telemetry.device_id)
    
    logging.info(telemetry)
    return {"status": "ok", "alerts": []}

@app.get("/devices/{hardware_id}/telemetry", response_model=List[TelemetryRecord])
def list_device_telemetry(hardware_id: str, limit: int = 50):
    limit = max(1, min(limit, 500))
    
    # Try Mongo first for historical data
    if MONGO_STORAGE:
        cursor = MONGO_STORAGE.db["telemetry"].find(
            {"device_id": hardware_id}
        ).sort("received_at", -1).limit(limit)
        results = list(cursor)
        # Convert _id to string or remove it
        for r in results:
            r.pop("_id", None)
        return [TelemetryRecord(**r) for r in results]
    
    # Fallback to memory cache
    return [t for t in telemetry_log if t.device_id == hardware_id][-limit:]

@app.get("/devices/{hardware_id}/telemetry/latest", response_model=TelemetryRecord)
def latest_device_telemetry(hardware_id: str):
    # Try to find latest in memory first (faster)
    for t in reversed(telemetry_log):
        if t.device_id == hardware_id:
            return t
            
    # Fallback to DB
    if MONGO_STORAGE:
        data = MONGO_STORAGE.db["telemetry"].find_one(
            {"device_id": hardware_id}, 
            sort=[("received_at", -1)]
        )
        if data:
            data.pop("_id", None)
            return TelemetryRecord(**data)

    raise HTTPException(status_code=404, detail="No telemetry found for this device.")

@app.get("/notifications", response_model=List[Notification])
def list_notifications(limit: int = 50):
    limit = max(1, min(limit, 200))
    # Combine memory and DB if needed, simplified here to return memory + DB fetch could be added
    return list(notifications)[-limit:]