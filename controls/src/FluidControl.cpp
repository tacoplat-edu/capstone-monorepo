#include "FluidControl.h"

void FluidControl::setup() {
    pinMode(PIN_PUMP_WATER, OUTPUT);
    pinMode(PIN_PUMP_NUTRIENT, OUTPUT);
    pinMode(PIN_VALVE_MAIN, OUTPUT);
    pinMode(PIN_MIXER_MOTOR, OUTPUT);
    stopAll();
    Serial.println("FLUID: System Initialized.");
}

void FluidControl::triggerWateringCycle() {
    if (!isWatering) {
        isWatering = true;
        cycleStep = 1;
        stepStartTime = millis();
        Serial.println("FLUID: Starting Watering Cycle.");
    }
}

void FluidControl::stopAll() {
    // SIMULATION: In real code, digitalWrite(PIN_X, LOW) for all actuators
}

void FluidControl::loop() {
    if (!isWatering) return;

    unsigned long elapsed = millis() - stepStartTime;

    switch (cycleStep) {
        case 1: // Dispense Nutrients (Pump 1)
            Serial.println("FLUID: [Step 1] Dispensing Nutrients...");
            if (elapsed > 2000) { // Run for 2 seconds (simulated)
                cycleStep = 2;
                stepStartTime = millis();
            }
            break;

        case 2: // Mix Solution (Mixer Motor)
            Serial.println("FLUID: [Step 2] Mixing Solution...");
            if (elapsed > 3000) { // Mix for 3 seconds
                cycleStep = 3;
                stepStartTime = millis();
            }
            break;

        case 3: // Distribute to Plant (Pump 2 + Valve)
            Serial.println("FLUID: [Step 3] Watering Plant...");
            if (elapsed > 4000) { 
                stopAll();
                isWatering = false;
                cycleStep = 0;
                Serial.println("FLUID: Cycle Complete.");
            }
            break;
    }
}