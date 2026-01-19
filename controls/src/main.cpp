#include <Arduino.h>
#include "Config.h"
#include "NetworkClient.h"
#include "TemperatureControl.h"
#include "FluidControl.h"
#include "LightingControl.h"

// --- Global Objects ---
NetworkClient network;
TemperatureControl tempControl;
FluidControl fluidControl;
LightingControl lightControl;

// --- State Variables ---
SystemTargets currentTargets; 

// --- Helper for Simulation ---
float simulateTempSensor() {
    static float temp = 22.0;
    temp += ((random(0, 20) - 10) / 100.0);
    return temp;
}

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_ONBOARD_LED, OUTPUT);

    Serial.println("--- PLANTBOX FIRMWARE STARTING ---");

    network.setup();
    tempControl.setup();
    fluidControl.setup();
    lightControl.setup();

    // Default Targets
    currentTargets.targetTemp = 24.0;
    currentTargets.triggerWatering = false;
}

void loop() {
    // 1. Network: Check for new reference values (Targets)
    network.fetchReferenceValues(currentTargets);

    // 2. Read Sensors
    // (Simulating the missing sensors to match the Python Data Model)
    SensorData currentReadings;
    currentReadings.air_temp_c = simulateTempSensor();
    currentReadings.humidity_pct = 60.0;        // Placeholder
    currentReadings.light_intensity_pct = 85.0; // Placeholder
    currentReadings.water_level_pct = 90.0;     // Placeholder
    currentReadings.nutrient_a_pct = 95.0;      // Placeholder
    currentReadings.moisture_pct = 45.0;        // Placeholder

    // 3. Run Control Loops
    tempControl.loop(currentReadings.air_temp_c, currentTargets.targetTemp);
    fluidControl.loop();
    lightControl.loop();

    // 4. Send Telemetry
    // We now pass the full struct
    network.sendTelemetryData(currentReadings);

    // 5. Handle Triggers from Backend
    if (currentTargets.triggerWatering) {
        fluidControl.triggerWateringCycle();
        currentTargets.triggerWatering = false; 
    }

    delay(CONTROL_LOOP_DELAY_MS);
}