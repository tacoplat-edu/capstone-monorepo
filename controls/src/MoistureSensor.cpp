#include "MoistureSensor.h"

void MoistureSensor::setup() {
    pinMode(PIN_MOISTURE_SENSOR, INPUT);
    Serial.println("MOISTURE: EK1940 Initialized.");
}

float MoistureSensor::getMoisturePercent() {
    int rawValue = analogRead(PIN_MOISTURE_SENSOR);
    
    // Map raw ADC value to a 0-100 percentage.
    // Note: Capacitive sensors read LOWER values when WET.
    float moisturePct = map(rawValue, airValue, waterValue, 0, 100);

    // Clamp values just in case readings drift outside your calibration bounds
    if (moisturePct > 100.0) moisturePct = 100.0;
    if (moisturePct < 0.0) moisturePct = 0.0;

    return moisturePct;
}