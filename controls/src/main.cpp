// pin 14 - PUMP1_EN
// pin 12 - SOL_EN
#include <Arduino.h>
#include "Config.h"
#include "NetworkClient.h"
#include "TemperatureControl.h"
#include "FluidControl.h"
#include "LightingControl.h"
#include "WaterLevelSensor.h"
#include "MoistureSensor.h"
#include "PowerMonitor.h"
#include <Wire.h>

// --- Global Objects ---
NetworkClient network;
TemperatureControl tempControl;
FluidControl fluidControl;
LightingControl lightControl;
WaterLevelSensor waterLevelSensor;
MoistureSensor moistureSensor;
PowerMonitor powerMon40(0x40, 0.01f);   // R9: 10 mΩ shunt
PowerMonitor powerMon41(0x41, 0.002f);  // R4: 2 mΩ shunt

// --- State Variables ---
SystemTargets currentTargets;
DemoState demoState;
DemoState lastDemoState;
bool firstRun = true;

#define DEBUG false

void setup() {

    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_ONBOARD_LED, OUTPUT);

    Serial.println("--- PLANTBOX FIRMWARE STARTING ---");

    network.setup();
    tempControl.setup();
    fluidControl.setup();
    lightControl.setup();
    waterLevelSensor.setup();
    moistureSensor.setup();
    powerMon40.setup();
    powerMon41.setup();
    delay(1000);

    currentTargets.targetTemp = 25.0;
    currentTargets.triggerWatering = false;

    // CSV header for CoolTerm capture
    if (DEBUG) {
        // Serial.println("time_ms,moisture_pct,pump_state,water_level_pct");
        Serial.println("time_ms,temp_c,target_c,heater_pwm,fan_state");
    }
}

void loop() {
    if (DEBUG) {
        // turn on nutrient pump
        digitalWrite(PIN_PUMP_NUTRIENT, HIGH);

        // sleep for 10 seconds
        delay(10000);

        // turn off nutrient pump
        digitalWrite(PIN_PUMP_NUTRIENT, LOW);

        // sleep for 10 seconds
        delay(10000);

        // turn on water pump
        // digitalWrite(PIN_PUMP_WATER, HIGH);

        // turn on mixer motor at low speed
        // fluidControl.setMixerSpeed(255);



        // --- Fluid control testing: moisture sensor + pump ---
        // float moisture = moistureSensor.getMoisturePercent();
        // bool pumpOn = moisture < 70.0;  // pump ON when soil is dry
        // Read water level sensor
        // float waterLevel = waterLevelSensor.getWaterLevelPercent();
        
        // digitalWrite(PIN_PUMP_WATER, pumpOn ? HIGH : LOW);

        // CSV row: time_ms, moisture_pct, pump_state, water_level_pct
        // Serial.print(millis());
        // Serial.print(",");
        // Serial.print(moisture, 1);
        // Serial.print(",");
        // Serial.print(pumpOn ? 1 : 0);
        // Serial.print(",");
        // Serial.println(waterLevel, 1);

        // --- Temperature control tuning loop ---
        // float currentTemp = tempControl.getTemperature();
        // float target = currentTargets.targetTemp;  // 25 °C
        
        // tempControl.loop(currentTemp, target);
        
        // CSV row: time_ms, temp_c, target_c, heater_pwm, fan_state
        // Serial.print(millis());
        // Serial.print(",");
        // Serial.print(currentTemp, 2);
        // Serial.print(",");
        // Serial.print(target, 1);
        // Serial.print(",");
        // Serial.print(tempControl.getHeaterPWM());
        // Serial.print(",");
        // Serial.println(tempControl.getFanState());
    }
    else {
        // Poll demo state from server (rate-limited internally)
        network.fetchDemoControl(demoState);

        SensorData currentReadings;
        currentReadings.air_temp_c = tempControl.getTemperature();
        currentReadings.water_level_pct = waterLevelSensor.getWaterLevelPercent();
        currentReadings.moisture_pct = moistureSensor.getMoisturePercent();
        currentReadings.power_mw = powerMon40.getPower_mW();

        // print sensor readings to serial monitor
        Serial.print("Air Temp: ");
        Serial.println(currentReadings.air_temp_c);
        Serial.print("Water Level: ");
        Serial.println(currentReadings.water_level_pct);
        Serial.print("Moisture: ");
        Serial.println(currentReadings.moisture_pct);
        Serial.print("Power: ");
        Serial.println(currentReadings.power_mw);

        // Remaining Placeholders
        currentReadings.humidity_pct = 60.0;
        currentReadings.light_intensity_pct = 85.0;
        currentReadings.nutrient_a_pct = 95.0;

        // --- Low Power Mode: hold all actuators at their last known state ---
        if (demoState.low_power_mode) {
            // Heater: restore last state
            if (lastDemoState.heater) {
                tempControl.setActuators(100, 1);
            } else {
                tempControl.setActuators(0, 0);
            }
            // Water pump: restore last state
            digitalWrite(PIN_PUMP_WATER, lastDemoState.water_pump ? HIGH : LOW);
            // Nutrient pump: restore last state
            digitalWrite(PIN_PUMP_NUTRIENT, lastDemoState.nutrient_pump ? HIGH : LOW);
            // Nutrient mixer: restore last state
            if (lastDemoState.nutrient_mixer) {
                fluidControl.setMixerSpeed(100);
            } else {
                fluidControl.stopMixer();
            }
            // Grow lights: restore last state
            lightControl.setLight(lastDemoState.grow_lights);
        } else if (demoState.demo_enabled) {
            // Track previous state to avoid spamming the hardware every 100ms

            if (firstRun) {
                Serial.println("DEMO: === Demo Mode ACTIVE ===");
                // Reset all actuators to OFF on entry — clears any state
                // left behind by the normal PID control loop
                tempControl.setActuators(0, 0);
                digitalWrite(PIN_PUMP_WATER, LOW);
                digitalWrite(PIN_PUMP_NUTRIENT, LOW);
                fluidControl.stopMixer();
                lightControl.setLight(false);
                firstRun = false;
            }

            // --- Heater: drive directly via setActuators (bypasses PID) ---
            if (demoState.heater != lastDemoState.heater) {
                if (demoState.heater) {
                    Serial.println("DEMO: Heater -> ON (PWM 255, Fan ON)");
                    tempControl.setActuators(255, 1);  // Full heat + fan for circulation
                } else {
                    Serial.println("DEMO: Heater -> OFF (PWM 0, Fan OFF)");
                    tempControl.setActuators(0, 0);
                }
            }

            // --- Water Pump: direct GPIO ---
            if (demoState.water_pump != lastDemoState.water_pump) {
                if (demoState.water_pump) {
                    Serial.println("DEMO: Water Pump -> ON");
                    digitalWrite(PIN_PUMP_WATER, HIGH);
                } else {
                    Serial.println("DEMO: Water Pump -> OFF");
                    digitalWrite(PIN_PUMP_WATER, LOW);
                }
            }

            // --- Nutrient Pump: direct GPIO ---
            if (demoState.nutrient_pump != lastDemoState.nutrient_pump) {
                if (demoState.nutrient_pump) {
                    Serial.println("DEMO: Nutrient Pump -> ON");
                    digitalWrite(PIN_PUMP_NUTRIENT, HIGH);
                } else {
                    Serial.println("DEMO: Nutrient Pump -> OFF");
                    digitalWrite(PIN_PUMP_NUTRIENT, LOW);
                }
            }

            // --- Nutrient Mixer: must use LEDC (pin is attached to PWM channel) ---
            if (demoState.nutrient_mixer != lastDemoState.nutrient_mixer) {
                if (demoState.nutrient_mixer) {
                    Serial.println("DEMO: Nutrient Mixer -> ON (full speed)");
                    fluidControl.setMixerSpeed(255);
                } else {
                    Serial.println("DEMO: Nutrient Mixer -> OFF");
                    fluidControl.stopMixer();
                }
            }

            // --- Grow Lights: use LightingControl helper ---
            if (demoState.grow_lights != lastDemoState.grow_lights) {
                if (demoState.grow_lights) {
                    Serial.println("DEMO: Grow Lights -> ON");
                    lightControl.setLight(true);
                } else {
                    Serial.println("DEMO: Grow Lights -> OFF");
                    lightControl.setLight(false);
                }
            }

            lastDemoState = demoState;

        } else {
            // Normal control logic
            tempControl.loop(currentReadings.air_temp_c, currentTargets.targetTemp);
            fluidControl.loop();

            if (currentTargets.triggerWatering) {
                fluidControl.triggerWateringCycle();
                currentTargets.triggerWatering = false;
            }
        }

        if (!demoState.demo_enabled && !demoState.low_power_mode) {
            lightControl.loop();
        }

        network.sendTelemetryData(currentReadings);
    }
    delay(CONTROL_LOOP_DELAY_MS);
}