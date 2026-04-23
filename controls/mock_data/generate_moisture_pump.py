"""
generate_moisture_pump.py
--------------------------
Generates a realistic CSV of PID-controlled soil moisture data
for the PlantBox capstone project.

Simulates:
  - EK1940 capacitive moisture sensor (0–100 %)
  - Water pump (ON/OFF via GPIO) controlled by PID
  - Soil moisture dynamics (slow absorption, gradual drying)

Performance specs (from Detailed Design: Controls — Water):
  - Overshoot:      <2 %
  - Settling time:   ≤5–10 min
  - Steady-state accuracy: within ±10% of target

Scenario:
  The soil starts dry (~30 %). PID ramps the pump to reach and
  maintain the target moisture (65 %). Includes a drying disturbance
  mid-run to show the controller recovering.

Output CSV columns:
  time_s, moisture_pct, target_pct, pump_state
"""

import csv
import math
import random
import os

# ──────────────────────────────────────────────────────────────────────
# ▸ CUSTOMISABLE CONSTANTS
# ──────────────────────────────────────────────────────────────────────

# Simulation timing
SIMULATION_DURATION_S = 1800       # 30 minutes total
DT = 0.5                           # Simulation time step (s)
SAMPLE_INTERVAL_S = 1.0            # CSV write interval (s)

# ── Target ──
TARGET_MOISTURE_PCT = 65.0         # Desired soil moisture (%)
CONTROL_ACCURACY_PCT = 10.0        # ±% band for "within spec"

# ── Initial condition ──
INITIAL_MOISTURE_PCT = 30.0        # Dry soil at start

# ── PID gains (tuned for slow soil response) ──
KP = 1.2                           # Proportional gain (moderate -- soil is slow)
KI = 0.01                          # Integral gain (very low -- prevent windup overshoot)
KD = 3.0                           # Derivative gain (high -- brake before target)

# ── Pump specs ──
PUMP_ON_THRESHOLD = 8.0            # PID output must exceed this to turn pump ON
PUMP_FLOW_EFFECT_PCT_PER_S = 0.14  # How fast pump raises moisture (%/s) -- drip rate

# ── Soil dynamics ──
SOIL_DRYING_RATE_PCT_PER_S = 0.012 # Natural evaporation/transpiration (%/s)
SOIL_ABSORPTION_TAU_S = 20.0       # Time constant for water absorption into soil
SOIL_MAX_MOISTURE_PCT = 100.0
SOIL_MIN_MOISTURE_PCT = 0.0

# ── Sensor noise (EK1940 capacitive sensor) ──
SENSOR_NOISE_STDDEV_PCT = 0.5      # Noise standard deviation (%)
SENSOR_QUANTISATION_PCT = 0.1      # ADC quantisation step

# ── Disturbance (e.g. hot/dry period or grow-light heat) ──
DISTURBANCE_TIME_S = 1000.0        # When disturbance starts
DISTURBANCE_DURATION_S = 120.0     # How long it lasts (s)
DISTURBANCE_EXTRA_DRY_RATE = 0.06  # Additional drying rate during disturbance (%/s)

# ── Overshoot spec ──
MAX_OVERSHOOT_PCT = 2.0            # Spec: <2%

# ── Output ──
OUTPUT_FILENAME = "moisture_pump_data.csv"


# ──────────────────────────────────────────────────────────────────────
# ▸ SIMULATION
# ──────────────────────────────────────────────────────────────────────

def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def quantise(val, step):
    return round(val / step) * step


def run_simulation():
    actual_moisture = INITIAL_MOISTURE_PCT
    integral = 0.0
    prev_error = 0.0
    water_in_transit = 0.0  # Water that's been pumped but not yet absorbed

    rows = []
    next_sample_time = 0.0
    t = 0.0

    while t <= SIMULATION_DURATION_S:
        # ── Sensor reading ──
        noise = random.gauss(0, SENSOR_NOISE_STDDEV_PCT)
        sensor_moisture = quantise(
            clamp(actual_moisture + noise, SOIL_MIN_MOISTURE_PCT, SOIL_MAX_MOISTURE_PCT),
            SENSOR_QUANTISATION_PCT
        )

        # ── PID controller ──
        error = TARGET_MOISTURE_PCT - sensor_moisture
        integral += error * DT
        integral = clamp(integral, -500.0, 500.0)  # Anti-windup

        derivative = (error - prev_error) / DT if DT > 0 else 0.0
        output = KP * error + KI * integral + KD * derivative
        prev_error = error

        # ── Bang-bang pump actuation from PID output ──
        # Positive output → pump ON; Negative → pump OFF
        pump_state = 1 if output > PUMP_ON_THRESHOLD else 0

        # Prevent pumping when close to or above target
        if actual_moisture > TARGET_MOISTURE_PCT - 2.0:
            pump_state = 0

        # ── Soil dynamics ──
        # 1. Drying (evaporation + transpiration)
        drying = SOIL_DRYING_RATE_PCT_PER_S * DT

        # 2. Disturbance
        if DISTURBANCE_TIME_S <= t < DISTURBANCE_TIME_S + DISTURBANCE_DURATION_S:
            drying += DISTURBANCE_EXTRA_DRY_RATE * DT

        # 3. Water absorption (first-order lag)
        if pump_state:
            water_in_transit += PUMP_FLOW_EFFECT_PCT_PER_S * DT

        absorbed = water_in_transit * (1.0 - math.exp(-DT / SOIL_ABSORPTION_TAU_S))
        water_in_transit -= absorbed

        # 4. Update actual moisture
        actual_moisture += absorbed - drying
        actual_moisture = clamp(actual_moisture, SOIL_MIN_MOISTURE_PCT, SOIL_MAX_MOISTURE_PCT)

        # ── Record sample ──
        if t >= next_sample_time:
            rows.append({
                "time_s": round(t, 2),
                "moisture_pct": round(sensor_moisture, 1),
                "target_pct": round(TARGET_MOISTURE_PCT, 1),
                "pump_state": pump_state,
            })
            next_sample_time += SAMPLE_INTERVAL_S

        t += DT

    return rows


def write_csv(rows):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, OUTPUT_FILENAME)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "time_s", "moisture_pct", "target_pct", "pump_state"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Wrote {len(rows)} rows -> {filepath}")
    return filepath


# ──────────────────────────────────────────────────────────────────────
# ▸ VERIFICATION
# ──────────────────────────────────────────────────────────────────────

def verify_specs(rows):
    target = TARGET_MOISTURE_PCT
    tolerance = target * (CONTROL_ACCURACY_PCT / 100.0)
    band_lo = target - tolerance
    band_hi = target + tolerance

    # Overshoot
    max_moisture = max(r["moisture_pct"] for r in rows)
    overshoot = max_moisture - target
    print(f"  Max overshoot:          {overshoot:+.1f} %   (spec: < {MAX_OVERSHOOT_PCT} %)  {'[PASS]' if overshoot < MAX_OVERSHOOT_PCT else '[FAIL]'}")

    # Settling time
    settling_time = None
    for i, r in enumerate(rows):
        if band_lo <= r["moisture_pct"] <= band_hi:
            stayed = all(band_lo <= rows[j]["moisture_pct"] <= band_hi
                         for j in range(i, min(i + 60, len(rows))))
            if stayed:
                settling_time = r["time_s"]
                break

    if settling_time is not None:
        print(f"  Settling time:          {settling_time:.0f} s ({settling_time/60:.1f} min)   (spec: <= 10 min)  {'[PASS]' if settling_time <= 600 else '[FAIL]'}")
    else:
        print("  Settling time:          NOT SETTLED  [FAIL]")

    # Steady-state accuracy (last 5 min)
    steady_rows = [r for r in rows if r["time_s"] > SIMULATION_DURATION_S - 300]
    if steady_rows:
        avg = sum(r["moisture_pct"] for r in steady_rows) / len(steady_rows)
        ss_error = abs(avg - target)
        pct_error = ss_error / target * 100
        print(f"  Steady-state avg:       {avg:.1f} %   (error: {pct_error:.1f}%, spec: < {CONTROL_ACCURACY_PCT}%)  {'[PASS]' if pct_error < CONTROL_ACCURACY_PCT else '[FAIL]'}")

    # Pump duty cycle (informational)
    pump_on_count = sum(1 for r in steady_rows if r["pump_state"] == 1)
    duty_pct = pump_on_count / len(steady_rows) * 100 if steady_rows else 0
    print(f"  Steady-state pump duty: {duty_pct:.1f} %   (informational)")


# ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("PlantBox — Moisture Sensor & Water Pump Mock Data Generator")
    print("=" * 60)
    print(f"  Target:     {TARGET_MOISTURE_PCT} %")
    print(f"  Initial:    {INITIAL_MOISTURE_PCT} %")
    print(f"  PID gains:  Kp={KP}, Ki={KI}, Kd={KD}")
    print(f"  Duration:   {SIMULATION_DURATION_S} s ({SIMULATION_DURATION_S/60:.0f} min)")
    print()

    rows = run_simulation()
    filepath = write_csv(rows)

    print()
    print("── Spec Verification ──")
    verify_specs(rows)
    print()
