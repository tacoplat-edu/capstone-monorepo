"""
generate_waterlevel_pump.py
-----------------------------
Generates a realistic CSV of water reservoir level data for the
PlantBox capstone project.

Simulates:
  - MS5837 pressure-based water level sensor (0–100 %)
  - Water pump consumption during watering cycles
  - Tank depletion over multiple watering events
  - Tank refill event (user action)

This is NOT a PID loop — water level is monitored (open-loop)
and the pump draws water from the reservoir during scheduled
watering cycles.  The data shows how the reservoir depletes
over a 24-hour day and is refilled.

Performance specs:
  - Water usage: <150 L/kg-yield
  - Tank depth: 0.30 m (from WaterLevelSensor.h)
  - Sensor accuracy: within ±10% of true level

Output CSV columns:
  time_s, water_level_pct, pump_state, event
"""

import csv
import math
import random
import os

# ──────────────────────────────────────────────────────────────────────
# ▸ CUSTOMISABLE CONSTANTS
# ──────────────────────────────────────────────────────────────────────

# Simulation timing
SIMULATION_DURATION_S = 86400      # 24 hours
DT = 1.0                           # Time step (s)
SAMPLE_INTERVAL_S = 30.0           # Write a CSV row every 30 s (2880 rows for 24 h)

# ── Tank geometry (matches WaterLevelSensor.h) ──
TANK_DEPTH_M = 0.30                # Total depth when 100% full
TANK_VOLUME_L = 8.0                # Reservoir capacity (litres)
INITIAL_LEVEL_PCT = 95.0           # Start nearly full

# ── Watering cycles ──
# Each cycle draws water for a fixed duration at a known flow rate.
# Based on FluidControl.cpp step 3: pump ON for 4000 ms.
WATERING_CYCLE_DURATION_S = 4.0    # Pump ON time per cycle (s)
PUMP_FLOW_RATE_L_PER_S = 0.015     # Peristaltic pump flow rate (~0.9 L/min)

# Watering schedule — times of day (in seconds from midnight)
# 3 cycles per day, evenly spaced
WATERING_TIMES_S = [
    6 * 3600,                       # 06:00
    12 * 3600,                      # 12:00
    18 * 3600,                      # 18:00
]

# ── Evaporation / slow loss ──
EVAPORATION_RATE_PCT_PER_HOUR = 0.08  # Very slow background loss (%/h)

# ── Refill event ──
REFILL_TIME_S = 20 * 3600          # User refills at 20:00
REFILL_TO_PCT = 98.0               # Refill to near-full
REFILL_RATE_PCT_PER_S = 2.0        # How fast the level rises during refill

# ── Sensor characteristics (MS5837) ──
SENSOR_NOISE_STDDEV_PCT = 0.3      # Pressure sensor noise mapped to %
SENSOR_OFFSET_PCT = 0.0            # Systematic offset (calibration error)
SENSOR_QUANTISATION_PCT = 0.1      # ADC quantisation

# ── Low-level warning ──
LOW_LEVEL_WARNING_PCT = 15.0       # Alert threshold
CONTROL_ACCURACY_PCT = 10.0        # ±% accuracy band

# ── Output ──
OUTPUT_FILENAME = "waterlevel_pump_data.csv"


# ──────────────────────────────────────────────────────────────────────
# ▸ SIMULATION
# ──────────────────────────────────────────────────────────────────────

def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def quantise(val, step):
    return round(val / step) * step


def volume_to_pct(volume_l):
    return (volume_l / TANK_VOLUME_L) * 100.0


def pct_to_volume(pct):
    return (pct / 100.0) * TANK_VOLUME_L


def run_simulation():
    water_volume_l = pct_to_volume(INITIAL_LEVEL_PCT)
    rows = []
    next_sample_time = 0.0
    t = 0.0

    # Pre-compute watering windows
    watering_windows = []
    for wt in WATERING_TIMES_S:
        watering_windows.append((wt, wt + WATERING_CYCLE_DURATION_S))

    refilling = False
    refill_done = False

    while t <= SIMULATION_DURATION_S:
        pump_state = 0
        event = ""

        # ── Check if currently in a watering window ──
        for (ws, we) in watering_windows:
            if ws <= t < we:
                pump_state = 1
                water_volume_l -= PUMP_FLOW_RATE_L_PER_S * DT
                event = "watering"
                break

        # ── Background evaporation ──
        evap_rate_per_s = (EVAPORATION_RATE_PCT_PER_HOUR / 100.0) * TANK_VOLUME_L / 3600.0
        water_volume_l -= evap_rate_per_s * DT

        # ── Refill event ──
        if not refill_done and t >= REFILL_TIME_S:
            refilling = True

        if refilling:
            target_volume = pct_to_volume(REFILL_TO_PCT)
            if water_volume_l < target_volume:
                refill_amount = (REFILL_RATE_PCT_PER_S / 100.0) * TANK_VOLUME_L * DT
                water_volume_l += refill_amount
                event = "refilling"
            else:
                refilling = False
                refill_done = True
                event = "refill_complete"

        # ── Clamp volume ──
        water_volume_l = clamp(water_volume_l, 0.0, TANK_VOLUME_L)

        # ── Sensor reading ──
        true_pct = volume_to_pct(water_volume_l)
        noise = random.gauss(0, SENSOR_NOISE_STDDEV_PCT)
        sensor_pct = quantise(
            clamp(true_pct + noise + SENSOR_OFFSET_PCT, 0.0, 100.0),
            SENSOR_QUANTISATION_PCT
        )

        # ── Low level warning ──
        if true_pct < LOW_LEVEL_WARNING_PCT and event == "":
            event = "low_level_warning"

        # ── Record sample ──
        if t >= next_sample_time:
            rows.append({
                "time_s": round(t, 1),
                "water_level_pct": round(sensor_pct, 1),
                "pump_state": pump_state,
                "event": event,
            })
            next_sample_time += SAMPLE_INTERVAL_S

        t += DT

    return rows


def write_csv(rows):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, OUTPUT_FILENAME)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "time_s", "water_level_pct", "pump_state", "event"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Wrote {len(rows)} rows -> {filepath}")
    return filepath


# ──────────────────────────────────────────────────────────────────────
# ▸ VERIFICATION
# ──────────────────────────────────────────────────────────────────────

def verify_specs(rows):
    # Water consumed per watering cycle
    water_per_cycle_l = PUMP_FLOW_RATE_L_PER_S * WATERING_CYCLE_DURATION_S
    cycles_per_day = len(WATERING_TIMES_S)
    daily_water_l = water_per_cycle_l * cycles_per_day
    monthly_water_l = daily_water_l * 30

    yield_kg_per_month = 1.0  # Target yield
    water_per_kg = monthly_water_l / yield_kg_per_month

    print(f"  Water per cycle:        {water_per_cycle_l*1000:.0f} mL")
    print(f"  Cycles per day:         {cycles_per_day}")
    print(f"  Daily consumption:      {daily_water_l:.2f} L   (excl. evaporation)")
    print(f"  Monthly consumption:    {monthly_water_l:.1f} L")
    print(f"  Water usage ratio:      {water_per_kg:.1f} L/kg-yield   (spec: < 150 L/kg-yield)  {'[PASS]' if water_per_kg < 150 else '[FAIL]'}")

    # Level range
    levels = [r["water_level_pct"] for r in rows]
    min_level = min(levels)
    max_level = max(levels)
    print(f"  Level range:            {min_level:.1f}% – {max_level:.1f}%")

    # Check sensor accuracy at known points
    print(f"  Sensor noise σ:         {SENSOR_NOISE_STDDEV_PCT} %   (within tank resolution)")

    # Refill recovery
    refill_rows = [r for r in rows if r["event"] == "refill_complete"]
    if refill_rows:
        print(f"  Refill recovery at:     t={refill_rows[0]['time_s']/3600:.1f} h  →  {refill_rows[0]['water_level_pct']:.1f}%")


# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("PlantBox — Water Level & Pump Mock Data Generator")
    print("=" * 60)
    print(f"  Tank volume:    {TANK_VOLUME_L} L")
    print(f"  Initial level:  {INITIAL_LEVEL_PCT} %")
    print(f"  Pump flow rate: {PUMP_FLOW_RATE_L_PER_S*1000:.0f} mL/s")
    print(f"  Watering times: {[f'{t/3600:.0f}:00' for t in WATERING_TIMES_S]}")
    print(f"  Duration:       {SIMULATION_DURATION_S/3600:.0f} h")
    print()

    rows = run_simulation()
    filepath = write_csv(rows)

    print()
    print("── Spec Verification ──")
    verify_specs(rows)
    print()
