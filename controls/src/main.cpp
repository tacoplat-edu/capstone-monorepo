#include <Arduino.h>
#include "Config.h"
#include "NetworkClient.h"
#include "TemperatureControl.h"
#include "FluidControl.h"
#include "LightingControl.h"
#include "WaterLevelSensor.h"
#include "MoistureSensor.h"

// --- Global Objects ---
NetworkClient network;
TemperatureControl tempControl;
FluidControl fluidControl;
LightingControl lightControl;
WaterLevelSensor waterLevelSensor;
MoistureSensor moistureSensor;

// --- State Variables ---
SystemTargets currentTargets;
DemoState demoState;

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
    delay(1000);

    currentTargets.targetTemp = 24.0;
    currentTargets.triggerWatering = false;
}

void loop() {
    if (DEBUG) {
        // test water level sensor
        float waterLevel = waterLevelSensor.getWaterLevelPercent();

        Serial.print("Water Level: ");
        Serial.println(waterLevel);

    }
    else {
        // Poll demo state from server (rate-limited internally)
        network.fetchDemoControl(demoState);

        SensorData currentReadings;
        currentReadings.air_temp_c = tempControl.getTemperature();
        currentReadings.water_level_pct = waterLevelSensor.getWaterLevelPercent();
        currentReadings.moisture_pct = moistureSensor.getMoisturePercent();

        // Remaining Placeholders
        currentReadings.humidity_pct = 60.0;
        currentReadings.light_intensity_pct = 85.0;
        currentReadings.nutrient_a_pct = 95.0;

        if (demoState.demo_enabled) {
            // Track previous state to avoid spamming the hardware every 100ms
            static DemoState lastDemoState;
            static bool firstRun = true;

            if (firstRun) {
                Serial.println("DEMO: === Demo Mode ACTIVE ===");
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

        if (!demoState.demo_enabled) {
            lightControl.loop();
        }

        network.sendTelemetryData(currentReadings);
    }
    delay(CONTROL_LOOP_DELAY_MS);
}