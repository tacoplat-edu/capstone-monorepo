from __future__ import annotations

import logging
import os
import sys
from collections import deque
from datetime import datetime, time
from pathlib import Path
from typing import Deque, Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

try:
    from libs.mailer.client import EmailClient, EmailConfig
except Exception:
    EmailClient = None
    EmailConfig = None

try:
    from libs.mongo.storage import MongoConfig, MongoStorage
except Exception:
    MongoConfig = None
    MongoStorage = None

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Plantbox API", version="0.1.0")

PLANT_PROFILES: Dict[str, Dict[str, float]] = {
    "lettuce": {
        "target_temperature_c": 21.0,
        "target_water_level_pct": 65.0,
        "target_flow_rate_lpm": 1.0,
        "light_hours": 14.0,
    },
    "basil": {
        "target_temperature_c": 24.0,
        "target_water_level_pct": 60.0,
        "target_flow_rate_lpm": 1.2,
        "light_hours": 16.0,
    },
    "strawberry": {
        "target_temperature_c": 20.0,
        "target_water_level_pct": 70.0,
        "target_flow_rate_lpm": 0.8,
        "light_hours": 12.0,
    },
}


class LightSchedule(BaseModel):
    start: time
    end: time


class NutrientSchedule(BaseModel):
    start: time
    end: time
    dose_ml: float = Field(..., ge=0)


class ConfigState(BaseModel):
    target_temperature_c: float = Field(..., ge=0)
    target_water_level_pct: float = Field(..., ge=0, le=100)
    target_flow_rate_lpm: float = Field(..., ge=0)
    light_schedule: LightSchedule
    nutrient_schedule: NutrientSchedule
    active_profile: str = "lettuce"


class TelemetryIn(BaseModel):
    temperature_c: float
    water_level_pct: float
    flow_rate_lpm: float
    light_lux: Optional[float] = None
    blackout_mode: bool = False
    captured_at: datetime = Field(default_factory=datetime.utcnow)


class TelemetryRecord(TelemetryIn):
    received_at: datetime


class Notification(BaseModel):
    id: str
    level: str
    message: str
    created_at: datetime
    telemetry: Optional[TelemetryIn] = None


def model_to_dict(model: BaseModel) -> Dict[str, object]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def build_default_config(profile_name: str = "lettuce") -> ConfigState:
    profile = PLANT_PROFILES.get(profile_name, PLANT_PROFILES["lettuce"])
    return ConfigState(
        target_temperature_c=profile["target_temperature_c"],
        target_water_level_pct=profile["target_water_level_pct"],
        target_flow_rate_lpm=profile["target_flow_rate_lpm"],
        light_schedule=LightSchedule(start=time(6, 0), end=time(20, 0)),
        nutrient_schedule=NutrientSchedule(
            start=time(8, 0), end=time(8, 30), dose_ml=15.0
        ),
        active_profile=profile_name,
    )


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
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"
    config = EmailConfig(
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        username=username,
        password=password,
        use_tls=use_tls,
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
        return MongoStorage(MongoConfig(uri=uri, db_name=db_name))
    except Exception as exc:
        logging.warning("Mongo disabled: %s", exc)
        return None


def deviation_pct(actual: float, target: float) -> float:
    if target <= 0:
        return 0.0
    return abs(actual - target) / target


def evaluate_telemetry(telemetry: TelemetryIn, config: ConfigState) -> List[str]:
    alerts: List[str] = []
    if deviation_pct(telemetry.temperature_c, config.target_temperature_c) > 0.10:
        alerts.append("Temperature drift above 10 percent.")
    if deviation_pct(telemetry.water_level_pct, config.target_water_level_pct) > 0.10:
        alerts.append("Water level drift above 10 percent.")
    if deviation_pct(telemetry.flow_rate_lpm, config.target_flow_rate_lpm) > 0.10:
        alerts.append("Flow rate drift above 10 percent.")
    if telemetry.blackout_mode:
        alerts.append("Blackout mode triggered.")
    return alerts


def evaluate_profile(telemetry: TelemetryIn, profile_name: str) -> List[str]:
    profile = PLANT_PROFILES.get(profile_name)
    if not profile:
        return []
    alerts: List[str] = []
    if deviation_pct(telemetry.temperature_c, profile["target_temperature_c"]) > 0.10:
        alerts.append(f"Temperature outside {profile_name} profile.")
    if deviation_pct(telemetry.water_level_pct, profile["target_water_level_pct"]) > 0.10:
        alerts.append(f"Water level outside {profile_name} profile.")
    if deviation_pct(telemetry.flow_rate_lpm, profile["target_flow_rate_lpm"]) > 0.10:
        alerts.append(f"Flow rate outside {profile_name} profile.")
    return alerts


def queue_notification(level: str, message: str, telemetry: TelemetryIn) -> Notification:
    note = Notification(
        id=str(uuid4()),
        level=level,
        message=message,
        created_at=datetime.utcnow(),
        telemetry=telemetry,
    )
    notifications.append(note)
    if EMAIL_SETTINGS:
        try:
            EMAIL_SETTINGS["client"].send_email(
                subject=f"Plantbox alert: {level.upper()}",
                body=message,
                from_email=EMAIL_SETTINGS["from_email"],
                to_emails=EMAIL_SETTINGS["to"],
            )
        except Exception as exc:
            logging.warning("Email send failed: %s", exc)
    return note


def store_telemetry(record: TelemetryRecord) -> None:
    if not MONGO_STORAGE:
        return
    try:
        MONGO_STORAGE.insert_one("telemetry", model_to_dict(record))
    except Exception as exc:
        logging.warning("Mongo insert failed: %s", exc)


config_state = build_default_config()
telemetry_log: Deque[TelemetryRecord] = deque(maxlen=500)
notifications: Deque[Notification] = deque(maxlen=200)
EMAIL_SETTINGS = load_email_settings()
MONGO_STORAGE = build_mongo_storage()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/config", response_model=ConfigState)
def get_config() -> ConfigState:
    return config_state


@app.post("/config", response_model=ConfigState)
def update_config(config: ConfigState) -> ConfigState:
    global config_state
    config_state = config
    return config_state


@app.get("/profiles")
def list_profiles() -> Dict[str, Dict[str, float]]:
    return PLANT_PROFILES


@app.post("/telemetry")
def post_telemetry(telemetry: TelemetryIn) -> Dict[str, object]:
    record = TelemetryRecord(**model_to_dict(telemetry), received_at=datetime.utcnow())
    telemetry_log.append(record)
    store_telemetry(record)

    alerts = evaluate_telemetry(telemetry, config_state)
    profile_alerts = evaluate_profile(telemetry, config_state.active_profile)
    if alerts or profile_alerts:
        all_alerts = alerts + profile_alerts
        level = "critical" if telemetry.blackout_mode else "warning"
        queue_notification(level, " ".join(all_alerts), telemetry)

    return {"status": "ok", "alerts": alerts, "profile_alerts": profile_alerts}


@app.get("/telemetry", response_model=List[TelemetryRecord])
def list_telemetry(limit: int = 50) -> List[TelemetryRecord]:
    limit = max(1, min(limit, 500))
    return list(telemetry_log)[-limit:]


@app.get("/telemetry/latest", response_model=TelemetryRecord)
def latest_telemetry() -> TelemetryRecord:
    if not telemetry_log:
        raise HTTPException(status_code=404, detail="No telemetry received yet.")
    return telemetry_log[-1]


@app.get("/notifications", response_model=List[Notification])
def list_notifications(limit: int = 50) -> List[Notification]:
    limit = max(1, min(limit, 200))
    return list(notifications)[-limit:]
