from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, time
from typing import Any, Dict, Tuple
from urllib import error, request

import pandas as pd
import streamlit as st

DEFAULT_SERVER_URL = os.getenv("PLANTBOX_SERVER_URL", "http://localhost:8000")

DEFAULT_PROFILES: Dict[str, Dict[str, float]] = {
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

DEFAULT_CONFIG: Dict[str, Any] = {
    "target_temperature_c": 21.0,
    "target_water_level_pct": 65.0,
    "target_flow_rate_lpm": 1.0,
    "light_schedule": {"start": "06:00:00", "end": "20:00:00"},
    "nutrient_schedule": {"start": "08:00:00", "end": "08:30:00", "dose_ml": 15.0},
    "active_profile": "lettuce",
}


def api_request(
    server_url: str, method: str, path: str, payload: Dict[str, Any] | None = None
) -> Tuple[bool, Dict[str, Any] | list, str]:
    url = f"{server_url.rstrip('/')}{path}"
    body = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=5) as response:
            raw = response.read().decode("utf-8") or "{}"
            return True, json.loads(raw), ""
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8") if exc.fp else ""
        return False, {}, f"HTTP {exc.code}: {raw or exc.reason}"
    except Exception as exc:
        return False, {}, str(exc)


def parse_time(value: Any, fallback: time) -> time:
    if isinstance(value, time):
        return value
    if isinstance(value, str):
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    return fallback


def generate_pairing_code() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(6))


def metric_delta(actual: float | None, target: float | None) -> str:
    if actual is None or target is None:
        return "n/a"
    return f"{actual - target:+.1f}"


st.set_page_config(page_title="Plantbox Brain", layout="wide")

st.title("Plantbox Brain")
st.write("Simple controls and live status for the greenhouse brain.")

with st.sidebar:
    st.header("Connection")
    server_url = st.text_input("API base URL", value=DEFAULT_SERVER_URL, key="server_url")
    st.caption("Example: http://localhost:8000")
    st.divider()
    st.header("Pairing")
    if "pairing_code" not in st.session_state:
        st.session_state.pairing_code = generate_pairing_code()
    st.code(st.session_state.pairing_code, language="text")
    if st.button("New pairing code"):
        st.session_state.pairing_code = generate_pairing_code()

health_ok, _, _ = api_request(server_url, "GET", "/health")

config_ok, config_data, config_error = api_request(server_url, "GET", "/config")
profiles_ok, profile_data, _ = api_request(server_url, "GET", "/profiles")
telemetry_ok, telemetry_data, telemetry_error = api_request(
    server_url, "GET", "/telemetry?limit=50"
)
notifications_ok, notifications_data, _ = api_request(
    server_url, "GET", "/notifications?limit=20"
)

profiles = profile_data if profiles_ok else DEFAULT_PROFILES
config = config_data if config_ok else DEFAULT_CONFIG
telemetry_list = telemetry_data if telemetry_ok and isinstance(telemetry_data, list) else []
notifications_list = (
    notifications_data if notifications_ok and isinstance(notifications_data, list) else []
)

if not health_ok:
    st.warning("API not reachable. Using defaults until the server comes online.")
    if config_error:
        st.caption(config_error)
    if telemetry_error:
        st.caption(telemetry_error)

latest = telemetry_list[-1] if telemetry_list else None

st.subheader("Live status")
if latest:
    col1, col2, col3 = st.columns(3)
    col1.metric(
        "Temperature (C)",
        f"{latest['temperature_c']:.1f}",
        metric_delta(latest["temperature_c"], config.get("target_temperature_c")),
    )
    col2.metric(
        "Water level (percent)",
        f"{latest['water_level_pct']:.1f}",
        metric_delta(latest["water_level_pct"], config.get("target_water_level_pct")),
    )
    col3.metric(
        "Flow rate (L/min)",
        f"{latest['flow_rate_lpm']:.2f}",
        metric_delta(latest["flow_rate_lpm"], config.get("target_flow_rate_lpm")),
    )
else:
    st.info("No telemetry yet. Send a reading from the ESP32 to populate the dashboard.")

if telemetry_list:
    df = pd.DataFrame(telemetry_list)
    if "captured_at" in df.columns:
        df["captured_at"] = pd.to_datetime(df["captured_at"])
        df = df.set_index("captured_at")
    st.line_chart(
        df[["temperature_c", "water_level_pct", "flow_rate_lpm"]],
        height=240,
    )

st.subheader("Controls")
light_schedule = config.get("light_schedule", {})
nutrient_schedule = config.get("nutrient_schedule", {})
default_light_start = parse_time(light_schedule.get("start"), time(6, 0))
default_light_end = parse_time(light_schedule.get("end"), time(20, 0))
default_nutrient_start = parse_time(nutrient_schedule.get("start"), time(8, 0))
default_nutrient_end = parse_time(nutrient_schedule.get("end"), time(8, 30))
default_nutrient_dose = float(nutrient_schedule.get("dose_ml", 15.0))

profile_names = list(profiles.keys())
active_profile = config.get("active_profile", profile_names[0] if profile_names else "")
if active_profile in profile_names:
    profile_index = profile_names.index(active_profile)
else:
    profile_index = 0

with st.form("controls_form"):
    target_temp = st.number_input(
        "Target temperature (C)",
        value=float(config.get("target_temperature_c", 21.0)),
        step=0.5,
    )
    target_water = st.slider(
        "Target water level (percent)",
        min_value=0,
        max_value=100,
        value=int(config.get("target_water_level_pct", 65)),
    )
    target_flow = st.number_input(
        "Target flow rate (L/min)",
        value=float(config.get("target_flow_rate_lpm", 1.0)),
        step=0.1,
    )
    st.caption("Light schedule")
    light_start = st.time_input("Lights on", value=default_light_start)
    light_end = st.time_input("Lights off", value=default_light_end)
    st.caption("Nutrient schedule")
    nutrient_start = st.time_input("Nutrient dosing start", value=default_nutrient_start)
    nutrient_end = st.time_input("Nutrient dosing end", value=default_nutrient_end)
    nutrient_dose = st.number_input(
        "Dose amount (ml)", value=float(default_nutrient_dose), step=1.0
    )
    profile_choice = st.selectbox(
        "Plant profile", options=profile_names, index=profile_index
    )
    submitted = st.form_submit_button("Save targets")

    if submitted:
        payload = {
            "target_temperature_c": float(target_temp),
            "target_water_level_pct": float(target_water),
            "target_flow_rate_lpm": float(target_flow),
            "light_schedule": {
                "start": light_start.strftime("%H:%M:%S"),
                "end": light_end.strftime("%H:%M:%S"),
            },
            "nutrient_schedule": {
                "start": nutrient_start.strftime("%H:%M:%S"),
                "end": nutrient_end.strftime("%H:%M:%S"),
                "dose_ml": float(nutrient_dose),
            },
            "active_profile": profile_choice,
        }
        ok, _, err = api_request(server_url, "POST", "/config", payload)
        if ok:
            st.success("Targets updated.")
        else:
            st.error(f"Update failed: {err}")

st.subheader("Plant profile tips")
profile = profiles.get(profile_choice) if profile_choice else None
if profile:
    st.write(
        f"{profile_choice.title()} prefers "
        f"{profile['target_temperature_c']}C, "
        f"{profile['target_water_level_pct']} percent water, "
        f"{profile['target_flow_rate_lpm']} L/min flow, "
        f"{profile['light_hours']} hours of light."
    )
else:
    st.info("No profile selected.")

with st.expander("Recent alerts"):
    if notifications_list:
        st.dataframe(notifications_list, use_container_width=True, height=240)
    else:
        st.write("No alerts yet.")
