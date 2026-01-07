#include "LightingControl.h"

void LightingControl::setup() {
    pinMode(PIN_GROW_LIGHTS, OUTPUT);
    Serial.println("LIGHT: System Initialized.");
}

void LightingControl::loop() {
    // In a real scenario, you need an NTP Client or RTC module to get real time.
    // For simulation, we will simply toggle lights based on a timer

    // Simulate "Day" is 10 seconds, "Night" is 10 seconds
    unsigned long timeVal = millis() / 1000;
    bool shouldBeOn = (timeVal % 20) < 10;

    if (shouldBeOn && !lightsOn) {
        lightsOn = true;
        Serial.println("LIGHT: Turning ON (Simulated Day)");
        // digitalWrite(PIN_GROW_LIGHTS, HIGH);
    } else if (!shouldBeOn && lightsOn) {
        lightsOn = false;
        Serial.println("LIGHT: Turning OFF (Simulated Night)");
        // digitalWrite(PIN_GROW_LIGHTS, LOW);
    }
}
