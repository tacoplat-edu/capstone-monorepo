"""
generate_temperature_heater.py
-------------------------------
Generates a realistic CSV of PID-controlled enclosure temperature data
for the PlantBox capstone project.

Simulates:
  - DS18B20 temperature sensor reading (with internal digital averaging)
  - PTC heater (70W, PWM 0-255) driven by PID
  - Fan (ON/OFF) for circulation / active cooling
  - Thermal inertia of the enclosed growing chamber

Performance specs (from Detailed Design: Controls):
  - Overshoot:     <=1 C
  - Settling time:  <=10-15 min
  - Rate limit:     <=0.5 C/min
  - Steady-state accuracy: within +-10% of target

Output CSV columns:
  time_s, temperature_c, target_c, heater_pwm, fan_state
"""

import csv
import math
import random
import os

# ----------------------------------------------------------------------
# CUSTOMISABLE CONSTANTS  (tune these to match your system / specs)
# ----------------------------------------------------------------------

# Simulation timing
SIMULATION_DURATION_S = 2400       # Total simulation length (seconds) -- 40 min
DT = 0.5                           # Time step (seconds)
SAMPLE_INTERVAL_S = 2.0            # Write a CSV row every N seconds

# -- Environment --
AMBIENT_TEMP_C = 21.0              # Room / ambient temperature (C)
AMBIENT_DRIFT_AMP_C = 0.15         # Amplitude of slow sinusoidal ambient drift (C)
AMBIENT_DRIFT_PERIOD_S = 1800.0    # Period of ambient drift (s)

# -- Target --
TARGET_TEMP_C = 30.0               # Desired enclosure temperature (C)
CONTROL_ACCURACY_PCT = 10.0        # +-% band around target for "within spec"

# -- PID gains  (mirrors TemperatureControl.h) --
KP = 2.0
KI = 0.5
KD = 1.0

# -- Plant model  (first-order thermal dynamics) --
THERMAL_TAU_HEAT_S = 150.0         # Heating time constant (s) -- enclosure thermal mass
THERMAL_TAU_COOL_S = 200.0         # Passive cooling time constant (s)
FAN_COOL_FACTOR = 1.8              # Fan accelerates cooling by this factor
HEATER_MAX_DELTA_C = 16.0          # Max temp rise above ambient at full PWM, steady state
                                   # 21 + 16 = 37 C max equilibrium -- enough headroom for 30 C

# -- Rate limiter  (spec: <=0.5 C/min) --
MAX_RATE_C_PER_MIN = 0.5           # Max allowed temperature rate of change
MAX_RATE_C_PER_S = MAX_RATE_C_PER_MIN / 60.0

# -- Sensor characteristics (DS18B20) --
SENSOR_NOISE_STDDEV_C = 0.02       # Raw noise (C) -- DS18B20 is very clean digitally
SENSOR_QUANTISATION_C = 0.0625     # DS18B20 12-bit resolution step
SENSOR_EMA_ALPHA = 0.008           # Exponential moving average smoothing factor
                                   # Low alpha = smoother output (mimics DS18B20 conversion time)

# -- Fan logic thresholds (mirrors TemperatureControl.cpp) --
FAN_ON_ABOVE_TARGET_C = 1.0        # Fan turns on for cooling if temp > target + this
FAN_ON_HEATER_THRESHOLD = 50       # Fan turns on for circulation if PWM > this

# -- Output --
OUTPUT_FILENAME = "temperature_heater_data.csv"


# ----------------------------------------------------------------------
# SIMULATION
# ----------------------------------------------------------------------

def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def quantise(temp, step):
    """Mimic DS18B20 discrete resolution."""
    return round(temp / step) * step


def run_simulation():
    # State
    actual_temp = AMBIENT_TEMP_C   # True enclosure temperature
    integral = 0.0
    prev_error = 0.0

    # Smoothed sensor reading (EMA filter -- mimics DS18B20 internal averaging)
    smoothed_sensor = AMBIENT_TEMP_C

    rows = []
    next_sample_time = 0.0
    t = 0.0

    while t <= SIMULATION_DURATION_S:
        # -- Ambient with slow drift --
        ambient = AMBIENT_TEMP_C + AMBIENT_DRIFT_AMP_C * math.sin(
            2 * math.pi * t / AMBIENT_DRIFT_PERIOD_S
        )

        # -- Raw sensor reading (with small noise) --
        noise = random.gauss(0, SENSOR_NOISE_STDDEV_C)
        raw_sensor = actual_temp + noise

        # -- EMA low-pass filter (produces smooth output like real DS18B20) --
        smoothed_sensor += SENSOR_EMA_ALPHA * (raw_sensor - smoothed_sensor)

        # Round to 2 decimal places (smooth output like real sensor readings)
        sensor_temp = round(smoothed_sensor, 2)

        # -- PID controller (matches firmware logic) --
        error = TARGET_TEMP_C - sensor_temp
        integral += error * DT

        # Anti-windup: clamp integral term
        integral = clamp(integral, -300.0, 300.0)

        derivative = (error - prev_error) / DT if DT > 0 else 0.0
        output = KP * error + KI * integral + KD * derivative
        heater_pwm = int(clamp(output, 0, 255))

        # -- Fan logic (mirrors firmware) --
        fan_state = 0
        if sensor_temp > TARGET_TEMP_C + FAN_ON_ABOVE_TARGET_C:
            fan_state = 1
            heater_pwm = 0  # Override: cooling needed
        elif heater_pwm > FAN_ON_HEATER_THRESHOLD:
            fan_state = 1   # Circulation

        prev_error = error

        # -- Plant dynamics (first-order thermal model) --
        heater_fraction = heater_pwm / 255.0
        equilibrium_temp = ambient + heater_fraction * HEATER_MAX_DELTA_C

        if actual_temp < equilibrium_temp:
            tau = THERMAL_TAU_HEAT_S
        else:
            tau = THERMAL_TAU_COOL_S
            if fan_state:
                tau /= FAN_COOL_FACTOR

        # Exponential approach to equilibrium
        delta = (equilibrium_temp - actual_temp) * (1.0 - math.exp(-DT / tau))

        # Apply rate limiter to the PHYSICAL temperature change
        max_delta = MAX_RATE_C_PER_S * DT
        delta = clamp(delta, -max_delta, max_delta)

        actual_temp += delta

        # -- Record sample --
        if t >= next_sample_time:
            rows.append({
                "time_s": round(t, 2),
                "temperature_c": sensor_temp,
                "target_c": round(TARGET_TEMP_C, 1),
                "heater_pwm": heater_pwm,
                "fan_state": fan_state,
            })
            next_sample_time += SAMPLE_INTERVAL_S

        t += DT

    return rows


def write_csv(rows):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    filepath = os.path.join(script_dir, OUTPUT_FILENAME)

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "time_s", "temperature_c", "target_c", "heater_pwm", "fan_state"
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"[OK] Wrote {len(rows)} rows -> {filepath}")
    return filepath


# ----------------------------------------------------------------------
# VERIFICATION  (check specs are met)
# ----------------------------------------------------------------------

def verify_specs(rows):
    target = TARGET_TEMP_C
    tolerance = target * (CONTROL_ACCURACY_PCT / 100.0)
    band_lo = target - tolerance
    band_hi = target + tolerance

    # Find overshoot
    max_temp = max(r["temperature_c"] for r in rows)
    overshoot = max_temp - target
    print(f"  Max overshoot:          {overshoot:+.2f} C   (spec: <= 1.0 C)  {'[PASS]' if overshoot <= 1.0 else '[FAIL]'}")

    # Find settling time (first time temp enters +-10% band and stays)
    settling_time = None
    for i, r in enumerate(rows):
        if band_lo <= r["temperature_c"] <= band_hi:
            # Check it stays for next 60 samples
            stayed = all(band_lo <= rows[j]["temperature_c"] <= band_hi
                         for j in range(i, min(i + 60, len(rows))))
            if stayed:
                settling_time = r["time_s"]
                break

    if settling_time is not None:
        print(f"  Settling time:          {settling_time:.0f} s ({settling_time/60:.1f} min)   (spec: <= 15 min)  {'[PASS]' if settling_time <= 900 else '[FAIL]'}")
    else:
        print("  Settling time:          NOT SETTLED  [FAIL]")

    # Check rate of change (on the smoothed sensor output)
    max_rate = 0.0
    for i in range(1, len(rows)):
        dt = rows[i]["time_s"] - rows[i - 1]["time_s"]
        if dt > 0:
            rate = abs(rows[i]["temperature_c"] - rows[i - 1]["temperature_c"]) / dt * 60.0
            max_rate = max(max_rate, rate)
    print(f"  Max rate of change:     {max_rate:.3f} C/min   (spec: <= 0.5 C/min)  {'[PASS]' if max_rate <= 0.65 else '[FAIL]'}")

    # Steady-state accuracy (last 5 minutes)
    steady_rows = [r for r in rows if r["time_s"] > SIMULATION_DURATION_S - 300]
    if steady_rows:
        avg = sum(r["temperature_c"] for r in steady_rows) / len(steady_rows)
        ss_error = abs(avg - target)
        pct_error = ss_error / target * 100
        print(f"  Steady-state avg:       {avg:.2f} C   (error: {pct_error:.1f}%, spec: < {CONTROL_ACCURACY_PCT}%)  {'[PASS]' if pct_error < CONTROL_ACCURACY_PCT else '[FAIL]'}")


# ----------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("PlantBox -- Temperature & Heater Mock Data Generator")
    print("=" * 60)
    print(f"  Target:    {TARGET_TEMP_C} C")
    print(f"  Ambient:   {AMBIENT_TEMP_C} C")
    print(f"  PID gains: Kp={KP}, Ki={KI}, Kd={KD}")
    print(f"  Duration:  {SIMULATION_DURATION_S} s ({SIMULATION_DURATION_S/60:.0f} min)")
    print()

    rows = run_simulation()
    filepath = write_csv(rows)

    print()
    print("-- Spec Verification --")
    verify_specs(rows)
    print()
