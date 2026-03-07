#include "FluidControl.h"

void FluidControl::setup() {
    pinMode(PIN_PUMP_WATER, OUTPUT);
    pinMode(PIN_PUMP_NUTRIENT, OUTPUT);
    pinMode(PIN_VALVE_MAIN, OUTPUT);

    // Initialize mixer motor with PWM via LEDC
    ledcSetup(_mixerChannel, MIXER_PWM_FREQ, _mixerResolution);
    ledcAttachPin(PIN_MIXER_MOTOR, _mixerChannel);
    ledcWrite(_mixerChannel, 0);
    Serial.printf("FLUID: Mixer PWM on GPIO %d | Ch %d | %d Hz | %d-bit\n",
                  PIN_MIXER_MOTOR, _mixerChannel, MIXER_PWM_FREQ, _mixerResolution);

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
    stopMixer();
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
                setMixerSpeed(255); // Full speed for mixing
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

void FluidControl::setMixerSpeed(uint8_t dutyCycle) {
    _mixerDuty = dutyCycle;
    ledcWrite(_mixerChannel, _mixerDuty);
    Serial.printf("FLUID: Mixer speed set to %d / %d\n", _mixerDuty, (1 << _mixerResolution) - 1);
}

void FluidControl::stopMixer() {
    _mixerDuty = 0;
    ledcWrite(_mixerChannel, 0);
    Serial.println("FLUID: Mixer stopped.");
}