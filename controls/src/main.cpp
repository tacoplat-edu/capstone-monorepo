#include <Arduino.h>
#include "Config.h"
#include "NetworkClient.h"
#include "TemperatureControl.h"
#include "FluidControl.h"
#include "LightingControl.h"
#include "WaterLevelSensor.h"

// --- Global Objects ---
NetworkClient network;
TemperatureControl tempControl;
FluidControl fluidControl;
LightingControl lightControl;
WaterLevelSensor waterLevelSensor;

// --- State Variables ---
SystemTargets currentTargets; 

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_ONBOARD_LED, OUTPUT);

    Serial.println("--- PLANTBOX FIRMWARE STARTING ---");

    network.setup();
    tempControl.setup();
    fluidControl.setup();
    lightControl.setup();
    waterLevelSensor.setup();
    delay(1000);  // Let sensors settle

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
    currentReadings.air_temp_c = tempControl.getTemperature();;
    currentReadings.humidity_pct = 60.0;        // Placeholder
    currentReadings.light_intensity_pct = 85.0; // Placeholder
    currentReadings.water_level_pct = waterLevelSensor.getWaterLevelPercent();
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