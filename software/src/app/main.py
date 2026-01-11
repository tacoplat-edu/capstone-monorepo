from __future__ import annotations

import json
import os
import time as time_lib
from datetime import datetime, time
from typing import Any, Dict, Tuple, Optional
from urllib import error, request

import pandas as pd
import streamlit as st

# --- Configuration ---
DEFAULT_SERVER_URL = os.getenv("PLANTBOX_SERVER_URL", "http://localhost:8000")
# We default to the ID used in your seed script
DEFAULT_DEVICE_ID = os.getenv("PLANTBOX_DEVICE_ID", "PlantBox-492")

# --- Helper Functions ---

def api_request(
    server_url: str, method: str, path: str, payload: Dict[str, Any] | None = None
) -> Tuple[bool, Any, str]:
    """Generic API wrapper."""
    url = f"{server_url.rstrip('/')}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload).encode("utf-8") if payload else None
    
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

def parse_time_str(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M:%S").time()
    except ValueError:
        return datetime.strptime(value, "%H:%M").time()

# --- Streamlit Layout ---

st.set_page_config(page_title="PlantBox Dashboard", layout="centered")

# 1. Sidebar Configuration
with st.sidebar:
    st.header("Connection")
    server_url = st.text_input("Server URL", value=DEFAULT_SERVER_URL)
    device_id = st.text_input("Device ID", value=DEFAULT_DEVICE_ID)
    st.caption(f"Connecting to: {server_url}/devices/{device_id}")
    
    if st.button("Refresh Data"):
        st.rerun()

# 2. Fetch Data
config_path = f"/devices/{device_id}/config"
telemetry_path = f"/devices/{device_id}/telemetry?limit=50"

config_ok, device_config, config_err = api_request(server_url, "GET", config_path)
telemetry_ok, telemetry_data, telemetry_err = api_request(server_url, "GET", telemetry_path)

if not config_ok:
    st.error(f"Could not connect to device. Server says: {config_err}")
    st.stop()

# 3. Main Dashboard Header
st.title(device_config.get("display_name", "My PlantBox"))

# Status Badge
is_online = device_config.get("is_online", False)
status_color = "green" if is_online else "red"
status_text = "PlantBox Active" if is_online else "Offline"
st.markdown(f":{status_color}[● {status_text}]")

# 4. Live Camera View (Placeholder)
if device_config.get("camera", {}).get("enabled"):
    st.image(
        "https://images.unsplash.com/photo-1550989460-0adf9ea622e2?q=80&w=1000&auto=format&fit=crop", 
        caption="Live Feed (Mock)", 
        use_container_width=True
    )

# 5. Sensor Cards (The "Fresh Data")
# We get the latest reading from the list (the API returns newest first or last depending on sort)
# Our API returns newest LAST in the list for graphing, so we take [-1]
latest = telemetry_data[-1] if (telemetry_ok and telemetry_data) else None

if latest:
    sensors = latest.get("sensors", {})
    
    # Top Row: Temp & Humidity
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Air Temp", f"{sensors.get('air_temp_c')}°C")
    with col2:
        st.metric("Humidity", f"{sensors.get('humidity_pct')}%")

    # Middle Row: Light & Schedule
    col3, col4 = st.columns(2)
    with col3:
        st.metric("Light Intensity", f"{sensors.get('light_intensity_pct')}%")
    with col4:
        # Display Schedule nicely
        schedule = device_config.get("light_schedule", {})
        start = schedule.get("start", "06:00")[:5] # strip seconds
        end = schedule.get("end", "18:00")[:5]
        st.metric("Light Schedule", f"{start} - {end}")

    # Bottom Row: Tanks
    st.markdown("---")
    st.subheader("Reservoir Levels")
    
    water_level = sensors.get("water_level_pct", 0)
    st.caption(f"Water Tank: {water_level}%")
    st.progress(int(water_level))

    nutrient_level = sensors.get("nutrient_a_pct", 0)
    st.caption(f"Nutrient A: {nutrient_level}%")
    st.progress(int(nutrient_level))

else:
    st.warning("No telemetry data received yet.")

# 6. Historical Graphs
st.subheader("History (24h)")
if telemetry_ok and telemetry_data:
    # Flatten the nested "sensors" dict for Pandas
    flat_data = []
    for record in telemetry_data:
        row = {
            "time": record["captured_at"],
            **record["sensors"]
        }
        flat_data.append(row)
        
    df = pd.DataFrame(flat_data)
    df["time"] = pd.to_datetime(df["time"])
    df = df.set_index("time")
    
    # Draw charts
    tab1, tab2 = st.tabs(["Environment", "Resources"])
    with tab1:
        st.line_chart(df[["air_temp_c", "humidity_pct", "light_intensity_pct"]])
    with tab2:
        st.line_chart(df[["water_level_pct", "nutrient_a_pct"]])

# 7. Settings Form (Updated for new schema)
with st.expander("Device Settings"):
    with st.form("settings_form"):
        st.write("Target Ranges")
        targets = device_config.get("targets", {})
        
        # Temp Settings
        t_min = st.number_input("Min Temp (°C)", value=targets.get("air_temp", {}).get("min", 18.0))
        t_max = st.number_input("Max Temp (°C)", value=targets.get("air_temp", {}).get("max", 28.0))
        
        # Schedule Settings
        st.write("Light Schedule")
        sch = device_config.get("light_schedule", {})
        s_start = st.time_input("Start Time", value=parse_time_str(sch.get("start", "06:00:00")))
        s_end = st.time_input("End Time", value=parse_time_str(sch.get("end", "18:00:00")))
        
        if st.form_submit_button("Save Changes"):
            # Construct the payload matching DeviceConfig model
            payload = device_config.copy()
            payload["targets"]["air_temp"]["min"] = t_min
            payload["targets"]["air_temp"]["max"] = t_max
            payload["light_schedule"]["start"] = s_start.strftime("%H:%M:%S")
            payload["light_schedule"]["end"] = s_end.strftime("%H:%M:%S")
            
            success, _, err = api_request(server_url, "POST", config_path, payload)
            if success:
                st.success("Settings saved!")
                time_lib.sleep(1)
                st.rerun()
            else:
                st.error(f"Failed to save: {err}")