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
    // SIMULATION: Only Print
    // digitalWrite(PIN_PUMP_WATER, LOW); ... etc
}

void FluidControl::loop() {
    if (!isWatering) return;

    unsigned long elapsed = millis() - stepStartTime;

    switch (cycleStep) {
        case 1: // Dispense Nutrients (Pump 1)
            Serial.println("FLUID: [Step 1] Dispensing Nutrients...");
            // digitalWrite(PIN_PUMP_NUTRIENT, HIGH);
            if (elapsed > 2000) { // Run for 2 seconds (simulated)
                // digitalWrite(PIN_PUMP_NUTRIENT, LOW);
                cycleStep = 2;
                stepStartTime = millis();
            }
            break;

        case 2: // Mix Solution (Mixer Motor)
            Serial.println("FLUID: [Step 2] Mixing Solution...");
            // digitalWrite(PIN_MIXER_MOTOR, HIGH);
            if (elapsed > 3000) { // Mix for 3 seconds
                // digitalWrite(PIN_MIXER_MOTOR, LOW);
                cycleStep = 3;
                stepStartTime = millis();
            }
            break;

        case 3: // Distribute to Plant (Pump 2 + Valve)
            Serial.println("FLUID: [Step 3] Watering Plant...");
            // digitalWrite(PIN_VALVE_MAIN, HIGH);
            // digitalWrite(PIN_PUMP_WATER, HIGH);
            // In real code, check flow sensor count here
            if (elapsed > 4000) {
                stopAll();
                isWatering = false;
                cycleStep = 0;
                Serial.println("FLUID: Cycle Complete.");
            }
            break;
    }
}
