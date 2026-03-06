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
        prevStep = -1; // Reset so step 1 entry fires
        stepStartTime = millis();
        Serial.println("FLUID: Starting Watering Cycle.");
    }
}

void FluidControl::stopAll() {
    digitalWrite(PIN_PUMP_WATER, LOW);
    digitalWrite(PIN_PUMP_NUTRIENT, LOW);
    digitalWrite(PIN_VALVE_MAIN, LOW);
    digitalWrite(PIN_MIXER_MOTOR, LOW);
}

void FluidControl::loop() {
    if (!isWatering) return;

    unsigned long elapsed = millis() - stepStartTime;
    bool stepEntry = (cycleStep != prevStep);

    switch (cycleStep) {
        case 1: // Dispense Nutrients (Pump 1)
            if (stepEntry) {
                stopAll();
                digitalWrite(PIN_PUMP_NUTRIENT, HIGH);
                Serial.println("FLUID: [Step 1] Dispensing Nutrients...");
                prevStep = cycleStep;
            }
            if (elapsed > 2000) {
                cycleStep = 2;
                stepStartTime = millis();
            }
            break;

        case 2: // Mix Solution (Mixer Motor)
            if (stepEntry) {
                stopAll();
                digitalWrite(PIN_MIXER_MOTOR, HIGH);
                Serial.println("FLUID: [Step 2] Mixing Solution...");
                prevStep = cycleStep;
            }
            if (elapsed > 3000) {
                cycleStep = 3;
                stepStartTime = millis();
            }
            break;

        case 3: // Distribute to Plant (Water Pump + Valve)
            if (stepEntry) {
                stopAll();
                digitalWrite(PIN_PUMP_WATER, HIGH);
                digitalWrite(PIN_VALVE_MAIN, HIGH);
                Serial.println("FLUID: [Step 3] Watering Plant...");
                prevStep = cycleStep;
            }
            if (elapsed > 4000) {
                stopAll();
                isWatering = false;
                cycleStep = 0;
                prevStep = -1;
                Serial.println("FLUID: Cycle Complete.");
            }
            break;
    }
}