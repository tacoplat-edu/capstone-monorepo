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
SystemTargets currentTargets; // Holds the data fetched from backend

// --- Helper for Simulation ---
float simulateTempSensor() {
    // Generates a fake temperature that slowly fluctuates around 22C
    static float temp = 22.0;
    temp += ((random(0, 20) - 10) / 100.0);
    return temp;
}

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_ONBOARD_LED, OUTPUT);

    Serial.println("--- PLANTBOX FIRMWARE STARTING ---");

    // Initialize Subsystems
    network.setup();
    tempControl.setup();
    fluidControl.setup();
    lightControl.setup();

    // Default Targets (Safety fallback)
    currentTargets.targetTemp = 24.0;
    currentTargets.triggerWatering = false;
}

void loop() {
    // 1. Network: Fetch latest setpoints
    network.pollBackend(currentTargets);

    // 2. Read Sensors (Simulated)
    float currentTemp = simulateTempSensor();

    // 3. Run Control Loops
    tempControl.loop(currentTemp, currentTargets.targetTemp);
    fluidControl.loop();
    lightControl.loop();

    // 4. Gather Telemetry Data
    // We retrieve the current state from our controllers to send to the cloud
    bool heaterState = (tempControl.getHeaterPWM() > 0); 
    bool fanState = tempControl.getFanState();
    bool wateringState = fluidControl.isWateringActive();

    // 5. Send Telemetry
    network.sendTelemetry(currentTemp, heaterState, fanState, wateringState);

    // 6. Handle Triggers from Backend
    if (currentTargets.triggerWatering) {
        fluidControl.triggerWateringCycle();
        currentTargets.triggerWatering = false; // Reset flag
    }

    delay(CONTROL_LOOP_DELAY_MS);
}