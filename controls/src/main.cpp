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

#define DEBUG true

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_ONBOARD_LED, OUTPUT);

    Serial.println("--- PLANTBOX FIRMWARE STARTING ---");

    // network.setup();
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


    SensorData currentReadings;
    currentReadings.air_temp_c = tempControl.getTemperature();
    currentReadings.water_level_pct = waterLevelSensor.getWaterLevelPercent();
    currentReadings.moisture_pct = moistureSensor.getMoisturePercent();

    // Remaining Placeholders
    currentReadings.humidity_pct = 60.0;
    currentReadings.light_intensity_pct = 85.0;
    currentReadings.nutrient_a_pct = 95.0;

    if (demoState.demo_enabled) {
        // Demo mode: activate only the requested actuators
        if (demoState.heater) {
            tempControl.loop(currentReadings.air_temp_c, 50.0); // High target to force heater ON
        } else {
            tempControl.loop(currentReadings.air_temp_c, currentTargets.targetTemp);
        }

        if (demoState.water_pump) {
            fluidControl.triggerWateringCycle();
        }

        if (demoState.nutrient_mixer) {
            digitalWrite(PIN_MIXER_MOTOR, HIGH);
        } else {
            digitalWrite(PIN_MIXER_MOTOR, LOW);
        }

    } else {
        // Normal control logic
        tempControl.loop(currentReadings.air_temp_c, currentTargets.targetTemp);
        fluidControl.loop();

        if (currentTargets.triggerWatering) {
            fluidControl.triggerWateringCycle();
            currentTargets.triggerWatering = false;
        }
    }

    lightControl.loop();

    network.sendTelemetryData(currentReadings);
    }
    delay(CONTROL_LOOP_DELAY_MS);
}