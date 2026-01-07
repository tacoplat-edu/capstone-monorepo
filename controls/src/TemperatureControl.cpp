#include "TemperatureControl.h"

void TemperatureControl::setup() {
    pinMode(PIN_HEATER, OUTPUT);
    pinMode(PIN_FAN, OUTPUT);
    Serial.println("TEMP: System Initialized.");
}

void TemperatureControl::loop(float currentTemp, float targetTemp) {
    unsigned long now = millis();
    float timeChange = (float)(now - lastTime) / 1000.0; // Seconds

    if (timeChange <= 0) return; // Prevent divide by zero on first loop

    // --- PID Calculation ---
    float error = targetTemp - currentTemp;
    integral += (error * timeChange);
    float derivative = (error - previousError) / timeChange;

    // Output is essentially a PWM duty cycle (0-255) for the heater
    float output = (Kp * error) + (Ki * integral) + (Kd * derivative);

    // Clamp output
    if (output > 255) output = 255;
    if (output < 0) output = 0;

    // --- Rate Limiting Logic (Report Sec 3.4) ---
    // If temp is rising too fast, kill heater even if PID wants it on
    // (This requires history of temp, simplified here for simulation)

    // --- Actuation ---
    // Fan logic: If heater is high, turn on fan to circulate.
    // Or if temp is too high, turn on fan to cool (Bang-bang control for cooling).
    int fanState = 0;
    if (currentTemp > targetTemp + 1.0) {
        fanState = 1; // Cooling needed
        output = 0;   // Heater off
    } else if (output > 50) {
        fanState = 1; // Circulation needed
    }

    setActuators((int)output, fanState);

    lastTime = now;
    previousError = error;
}

void TemperatureControl::setActuators(int heaterPWM, int fanState) {
    // SIMULATION: Print instead of writing
    // In real code: analogWrite(PIN_HEATER, heaterPWM);
    // In real code: digitalWrite(PIN_FAN, fanState);

    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 2000) { // Don't spam serial
        Serial.printf("TEMP_CTRL: Heater PWM: %d | Fan: %s\n", heaterPWM, fanState ? "ON" : "OFF");

        // Visual feedback on LED if Heater is working hard
        if (heaterPWM > 100) digitalWrite(PIN_ONBOARD_LED, HIGH);
        else digitalWrite(PIN_ONBOARD_LED, LOW);

        lastPrint = millis();
    }
}
