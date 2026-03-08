# streamlit run main.py
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
DEFAULT_SERVER_URL = os.getenv("PLANTBOX_SERVER_URL", "http://127.0.0.1:8000")
# We default to the ID used in your seed script
DEFAULT_DEVICE_ID = os.getenv("PLANTBOX_DEVICE_ID", "PlantBox-1")

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

# 2. Check if device is initialized
exists_path = f"/devices/{device_id}/exists"
exists_ok, exists_data, exists_err = api_request(server_url, "GET", exists_path)

if not exists_ok:
    st.error(f"Could not reach server: {exists_err}")
    st.stop()

# Load plant profiles
import pathlib
plants_file = pathlib.Path(__file__).parent / "plants.json"
with open(plants_file) as f:
    PLANT_PROFILES = json.load(f)

if not exists_data.get("exists", False):
    # --- Onboarding Screen ---
    st.title("🌱 Welcome to PlantBox")
    st.markdown("Your PlantBox hasn't been set up yet. Let's get started!")

    with st.form("onboarding_form"):
        st.text_input("PlantBox ID", value=device_id, disabled=True)

        email = st.text_input("Your Email", placeholder="you@example.com")

        # Build searchable plant list
        plant_keys = list(PLANT_PROFILES.keys())
        plant_labels = [k.replace("_", " ").title() for k in plant_keys]
        # Put "Other" at the end
        other_idx = plant_keys.index("other") if "other" in plant_keys else len(plant_keys) - 1

        selected_label = st.selectbox(
            "What are you growing?",
            options=plant_labels,
            index=0,
        )

        submitted = st.form_submit_button("Initialize PlantBox")

    if submitted:
        if not email or not email.strip():
            st.error("Please enter your email address.")
            st.stop()

        # Map label back to key
        selected_idx = plant_labels.index(selected_label)
        selected_key = plant_keys[selected_idx]
        profile = PLANT_PROFILES[selected_key]

        display_name = f"My {selected_label}"

        payload = {
            "hardware_id": device_id,
            "display_name": display_name,
            "owner_id": email.strip(),
            "plant_type": selected_key,
            "light_schedule": {"start": "06:00:00", "end": "18:00:00"},
            "targets": {
                "air_temp": profile["air_temp"],
            },
        }

        update_path = f"/devices/{device_id}/config"
        ok, _, err = api_request(server_url, "POST", update_path, payload)
        if ok:
            st.success(f"PlantBox initialized as \"{display_name}\"! Loading dashboard...")
            time_lib.sleep(1)
            st.rerun()
        else:
            st.error(f"Failed to initialize: {err}")

    st.stop()

# 3. Fetch Data (device exists — show dashboard)
fetch_config_path = f"/devices/{device_id}/fetchRefVals"
update_config_path = f"/devices/{device_id}/config"
telemetry_path = f"/devices/{device_id}/telemetry?limit=50"

config_ok, device_config, config_err = api_request(server_url, "GET", fetch_config_path)
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


# 5. Sensor Cards (The "Fresh Data")
# We get the latest reading from the list (the API returns newest first or last depending on sort)
# Our API returns newest LAST in the list for graphing, so we take [-1]
latest = telemetry_data[-1] if (telemetry_ok and telemetry_data) else None

if latest:
    sensors = latest.get("sensors", {})
    
    # Top Row: Temp, Light & Schedule
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Air Temp", f"{sensors.get('air_temp_c')}°C")
    with col2:
        st.metric("Light Intensity", f"{sensors.get('light_intensity_pct')}%")
    with col3:
        # Display Schedule nicely
        schedule = device_config.get("light_schedule", {})
        start = schedule.get("start", "06:00")[:5] # strip seconds
        end = schedule.get("end", "18:00")[:5]
        st.metric("Light Schedule", f"{start} - {end}")

    # Bottom Row: Tanks
    st.markdown("---")
    st.subheader("Reservoir Levels")
    
    water_level = sensors.get("water_level_pct", 0)
    if water_level < 0:
        st.caption("Water Tank: No Sensor")
        st.progress(0)
    else:
        st.caption(f"Water Tank: {water_level}%")
        st.progress(max(0, min(100, int(water_level))))

    nutrient_level = sensors.get("nutrient_a_pct", 0)
    st.caption(f"Nutrient A: {nutrient_level}%")
    st.progress(max(0, min(100, int(nutrient_level))))

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
        st.line_chart(df[["air_temp_c", "light_intensity_pct"]])
    with tab2:
        st.line_chart(df[["water_level_pct", "nutrient_a_pct"]])

# --- Demo Controls ---
demo_path = f"/devices/{device_id}/demo_control"
demo_ok, demo_data, demo_err = api_request(server_url, "GET", demo_path)
demo_state = demo_data if demo_ok else {}

st.subheader("🎛️ Demo Controls")
dc0, dc1, dc2, dc3, dc4 = st.columns(5)

with dc0:
    demo_enabled = st.toggle("🚀 Demo Mode", value=demo_state.get("demo_enabled", False), key="demo_enabled")
with dc1:
    heater_on = st.toggle("🔥 Heater", value=demo_state.get("heater", False), key="demo_heater")
with dc2:
    water_on = st.toggle("💧 Water Pump", value=demo_state.get("water_pump", False), key="demo_water")
with dc3:
    nutrient_on = st.toggle("🧪 Nutrient Mixer", value=demo_state.get("nutrient_mixer", False), key="demo_nutrient")
with dc4:
    lights_on = st.toggle("💡 Grow Lights", value=demo_state.get("grow_lights", False), key="demo_lights")

# Detect if any toggle changed and push the update
new_demo = {"demo_enabled": demo_enabled, "heater": heater_on, "water_pump": water_on, "nutrient_mixer": nutrient_on, "grow_lights": lights_on}
if new_demo != {k: demo_state.get(k, False) for k in ("demo_enabled", "heater", "water_pump", "nutrient_mixer", "grow_lights")}:
    ok, _, err = api_request(server_url, "POST", demo_path, new_demo)
    if ok:
        st.toast("Actuator state updated!", icon="✅")
    else:
        st.error(f"Failed to update actuator: {err}")

# 7. Settings Form (Updated for new schema)
with st.expander("Device Settings"):
    with st.form("settings_form"):
        st.subheader("Plant Name")
        plant_name = st.text_input("Display Name", value=device_config.get("display_name", "My PlantBox"))

        st.divider()
        st.subheader("Target Ranges")
        
        # Get defaults safely
        targets = device_config.get("targets", {})
        def get_target(key, param, default):
            # Safe float conversion
            val = targets.get(key, {}).get(param, default)
            return float(val)

        st.markdown("#### Air Temp (°C)")
        t_min = st.number_input("Min", value=get_target("air_temp", "min", 18.0), step=0.25, key="t_min")
        t_max = st.number_input("Max", value=get_target("air_temp", "max", 28.0), step=0.25, key="t_max")

        st.markdown("#### Water Level (%)")
        w_min = st.number_input("Min Level", value=get_target("water_level", "min", 50.0), step=1.0, key="w_min")
        w_max = st.number_input("Max Level", value=get_target("water_level", "max", 100.0), step=1.0, key="w_max")

        st.divider()
        st.subheader("Light Schedule")
        sch = device_config.get("light_schedule", {})
        
        col_c, col_d = st.columns(2)
        with col_c:
            s_start = st.time_input("Start Time", value=parse_time_str(sch.get("start", "06:00:00")))
        with col_d:
            s_end = st.time_input("End Time", value=parse_time_str(sch.get("end", "18:00:00")))
        
        if st.form_submit_button("Save Changes"):
            # Deep copy to avoid mutating the original reference before send
            payload = json.loads(json.dumps(device_config))
            
            # Update Plant Name
            payload["display_name"] = plant_name
            
            # Ensure keys exist
            if "targets" not in payload: payload["targets"] = {}
            
            # Update Temp
            if "air_temp" not in payload["targets"]: payload["targets"]["air_temp"] = {}
            payload["targets"]["air_temp"]["min"] = t_min
            payload["targets"]["air_temp"]["max"] = t_max

            # Update Water
            if "water_level" not in payload["targets"]: payload["targets"]["water_level"] = {}
            payload["targets"]["water_level"]["min"] = w_min
            payload["targets"]["water_level"]["max"] = w_max
            
            # Update Schedule
            if "light_schedule" not in payload: payload["light_schedule"] = {}
            payload["light_schedule"]["start"] = s_start.strftime("%H:%M:%S")
            payload["light_schedule"]["end"] = s_end.strftime("%H:%M:%S")
            
            success, _, err = api_request(server_url, "POST", update_config_path, payload)
            if success:
                st.success("Settings saved to MongoDB!")
                time_lib.sleep(1)
                st.rerun()
            else:
                st.error(f"Failed to save: {err}")