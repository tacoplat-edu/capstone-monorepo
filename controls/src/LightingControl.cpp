#include "LightingControl.h"

void LightingControl::setup() {
    pinMode(PIN_GROW_LIGHTS, OUTPUT);
    digitalWrite(PIN_GROW_LIGHTS, LOW);
    Serial.println("LIGHT: LED Grow Lights Initialized.");
}

void LightingControl::loop() {
    // TODO: Replace with NTP or RTC for real day/night schedule.
    // Current placeholder: 10s ON / 10s OFF cycle for testing.
    unsigned long timeVal = millis() / 1000;
    bool shouldBeOn = (timeVal % 20) < 10;

    if (shouldBeOn && !lightsOn) {
        lightsOn = true;
        digitalWrite(PIN_GROW_LIGHTS, HIGH);
        Serial.println("LIGHT: Grow Lights ON");
    } else if (!shouldBeOn && lightsOn) {
        lightsOn = false;
        digitalWrite(PIN_GROW_LIGHTS, LOW);
        Serial.println("LIGHT: Grow Lights OFF");
    }
}

void LightingControl::setLight(bool on) {
    lightsOn = on;
    digitalWrite(PIN_GROW_LIGHTS, on ? HIGH : LOW);
    Serial.printf("LIGHT: Grow Lights %s\n", on ? "ON" : "OFF");
}
