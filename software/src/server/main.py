# uvicorn main:app --host 0.0.0.0 --port 8000
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

import dotenv
dotenv.load_dotenv()


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

app = FastAPI(title="Plantbox API", version="0.2.1")

# --- Default/Fallback Data ---
DEFAULT_TARGETS = {
    "air_temp": {"min": 18.0, "max": 28.0},
    "water_level": {"min": 50.0, "max": 100.0},
}

# --- Pydantic Models ---

class LightSchedule(BaseModel):
    start: time
    end: time

class TargetRange(BaseModel):
    min: float
    max: float


# Replaces the old ConfigState to match the new UI/DB schema
class DeviceConfig(BaseModel):
    hardware_id: str
    display_name: str = "My PlantBox"
    owner_id: str
    plant_type: str = "other"
    
    # Schedules shown in the UI
    light_schedule: LightSchedule
    
    # Thresholds (Reference Values)
    targets: Dict[str, TargetRange] = {
        "air_temp": TargetRange(**DEFAULT_TARGETS["air_temp"]),
        "water_level": TargetRange(**DEFAULT_TARGETS["water_level"])
    }
    
    # Heartbeat tracking
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    is_online: bool = True
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SensorReadings(BaseModel):
    air_temp_c: float = Field(..., description="Air Temperature in Celsius")
    humidity_pct: float = Field(0.0, ge=0, le=100, description="Relative Humidity")
    light_intensity_pct: float = Field(..., ge=0, le=100, description="Light Sensor Level")
    water_level_pct: float = Field(..., ge=-1, le=100, description="Water Level in Reservoir (-1 = no reading)")
    nutrient_a_pct: float = Field(..., ge=0, le=100, description="Nutrient Tank A Level")
    moisture_pct: float = Field(..., ge=0, le=100, description="Moisture Sensor Level")

class TelemetryIn(BaseModel):
    device_id: str
    sensors: SensorReadings
    captured_at: datetime = Field(default_factory=datetime.utcnow)

class TelemetryRecord(TelemetryIn):
    received_at: datetime
    metadata: Dict[str, Any] = {} 

class DemoControl(BaseModel):
    hardware_id: str
    demo_enabled: bool = False
    low_power_mode: bool = False
    heater: bool = False
    water_pump: bool = False
    nutrient_mixer: bool = False
    grow_lights: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
        sys.exit("MONGO_URI not set")
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
    sensors = telemetry.sensors
    targets = config.targets

    # Example Check: Air Temp
    if "air_temp" in targets:
       t = targets["air_temp"]
       if sensors.air_temp_c < t.min or sensors.air_temp_c > t.max:
           alerts.append(f"Temp {sensors.air_temp_c}°C out of range ({t.min}-{t.max})")


    # Example Check: Water Level
    if "water_level" in targets:
       w = targets["water_level"]
       if sensors.water_level_pct < w.min: 
            alerts.append(f"Water level low: {sensors.water_level_pct}%")

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
    return {"status": "running"}

@app.get("/devices/{hardware_id}/exists")
def device_exists(hardware_id: str) -> Dict[str, Any]:
    """Check if a device has been initialized in MongoDB."""
    if MONGO_STORAGE:
        data = MONGO_STORAGE.db["devices"].find_one({"hardware_id": hardware_id})
        return {"exists": data is not None}
    return {"exists": False}

# Endpoint 1: Fetch Reference Values (Config)
@app.get("/devices/{hardware_id}/fetchRefVals", response_model=DeviceConfig)
def fetch_reference_values(hardware_id: str):
    config = get_or_create_device_config(hardware_id)
    
    # Calculate online status dynamically
    time_diff = datetime.utcnow() - config.last_seen
    config.is_online = time_diff < timedelta(minutes=2)
    
    return config

# Allow updating config via standard REST path (optional helper)
# Helper for Recursive Updates
def deep_merge(source: Dict[str, Any], destination: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges source into destination."""
    for key, value in source.items():
        if isinstance(value, dict):
            node = destination.setdefault(key, {})
            deep_merge(value, node)
        else:
            destination[key] = value
    return destination

@app.post("/devices/{hardware_id}/config", response_model=Dict[str, Any])
def update_device_config(hardware_id: str, payload: Dict[str, Any]):
    """
    Accepts a partial or full configuration update.
    Deep-merges the payload into the existing MongoDB document.
    """
    # 1. Fetch existing (or defaults if missing)
    # We use get_or_create_device_config but want it as a dict to merge
    existing_model = get_or_create_device_config(hardware_id)
    existing_data = model_to_dict(existing_model)
    
    # 2. Merge changes
    # Ensure hardware_id isn't tampered with if passed
    if "hardware_id" in payload and payload["hardware_id"] != hardware_id:
        raise HTTPException(status_code=400, detail="Hardware ID mismatch")
    
    updated_data = deep_merge(payload, existing_data)
    updated_data["updated_at"] = datetime.utcnow()
    
    # 3. Save to Mongo
    if MONGO_STORAGE:
        MONGO_STORAGE.db["devices"].update_one(
            {"hardware_id": hardware_id},
            {"$set": updated_data},
            upsert=True
        )
        
    return updated_data

# Endpoint 2: Send Telemetry
@app.post("/sendTelemetry")
def send_telemetry(telemetry: TelemetryIn) -> Dict[str, Any]:
    # 1. Update Device "Last Seen" and Status
    if MONGO_STORAGE:
        MONGO_STORAGE.db["devices"].update_one(
            {"hardware_id": telemetry.device_id},
            {"$set": {"last_seen": datetime.utcnow(), "is_online": True}}
        )

    # 2. Store Telemetry
    record = TelemetryRecord(
        **model_to_dict(telemetry),
        received_at=datetime.utcnow(),
        metadata={"processed_by": "plantbox-v2"}
    )
    telemetry_log.append(record)
    store_telemetry(record)

    # 3. Check Alerts against current config
    config = get_or_create_device_config(telemetry.device_id)
    alerts = check_alerts(telemetry, config)
    
    if alerts:
        queue_notification("warning", "; ".join(alerts), telemetry.device_id)

    logging.info(f"Telemetry received for {telemetry.device_id}")
    return {"status": "ok", "alerts": alerts}

@app.get("/devices/{hardware_id}/telemetry", response_model=List[TelemetryRecord])
def list_device_telemetry(hardware_id: str, limit: int = 50):
    limit = max(1, min(limit, 500))
    
    # Try Mongo first for historical data
    if MONGO_STORAGE:
        cursor = MONGO_STORAGE.db["telemetry"].find(
            {"device_id": hardware_id}
        ).sort("received_at", -1).limit(limit)
        results = list(cursor)
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
    return list(notifications)[-limit:]

# --- Demo Control Endpoints ---

@app.get("/devices/{hardware_id}/demo_control", response_model=DemoControl)
def get_demo_control(hardware_id: str):
    """Fetch the current demo actuator states from the demo_control collection."""
    if MONGO_STORAGE:
        data = MONGO_STORAGE.db["demo_control"].find_one({"hardware_id": hardware_id})
        if data:
            data.pop("_id", None)
            return DemoControl(**data)
    # Return defaults if no document exists
    return DemoControl(hardware_id=hardware_id)

@app.post("/devices/{hardware_id}/demo_control", response_model=DemoControl)
def update_demo_control(hardware_id: str, payload: Dict[str, Any]):
    """Update actuator toggle states in the demo_control collection."""
    # Build the update from current state + incoming changes
    existing = get_demo_control(hardware_id)
    existing_data = model_to_dict(existing)
    updated_data = deep_merge(payload, existing_data)
    updated_data["hardware_id"] = hardware_id
    updated_data["updated_at"] = datetime.utcnow()

    if MONGO_STORAGE:
        MONGO_STORAGE.db["demo_control"].update_one(
            {"hardware_id": hardware_id},
            {"$set": updated_data},
            upsert=True
        )

    return DemoControl(**updated_data)