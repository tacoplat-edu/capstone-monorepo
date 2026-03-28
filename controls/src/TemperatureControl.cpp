#include "TemperatureControl.h"

// ESP32 LEDC PWM config for PTC Heater
#define HEATER_LEDC_CHANNEL  0
#define HEATER_LEDC_FREQ     5000   // 5 kHz
#define HEATER_LEDC_RES      8      // 8-bit (0-255)

void TemperatureControl::setup() {
    // PTC Heater — PWM via LEDC
    ledcSetup(HEATER_LEDC_CHANNEL, HEATER_LEDC_FREQ, HEATER_LEDC_RES);
    ledcAttachPin(PIN_HEATER, HEATER_LEDC_CHANNEL);
    // Fan — digital ON/OFF
    pinMode(PIN_FAN, OUTPUT);
    
    oneWire = new OneWire(PIN_TEMP_SENSOR); 
    sensors = new DallasTemperature(oneWire);
    sensors->begin();
    
    Serial.print("TEMP: DS18B20 devices found: ");
    Serial.println(sensors->getDeviceCount());
    Serial.println("TEMP: System Initialized.");
}

float TemperatureControl::getTemperature() {
    sensors->requestTemperatures();
    // delay(750);  // DS18B20 conversion time
    float tempC = sensors->getTempCByIndex(0);
    
    if (tempC == DEVICE_DISCONNECTED_C) {
        Serial.println("TEMP: DS18B20 disconnected - check wiring");
        return -999.0;  // Error value
    }
    
    return tempC;
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

    // --- Actuation Logic ---
    // Fan logic: If temp is too high, fan cools. If heater is high, fan circulates.
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
    // 1. SAVE STATE for Telemetry
    currentHeaterPWM = heaterPWM;
    currentFanState = (fanState > 0);

    // 2. DRIVE ACTUATORS
    // PTC Heater (12V 70W) — PWM via LEDC channel
    ledcWrite(HEATER_LEDC_CHANNEL, heaterPWM);
    // Fan — simple ON/OFF
    digitalWrite(PIN_FAN, fanState);

    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 2000) {
        Serial.printf("TEMP_CTRL: Heater PWM: %d | Fan: %s\n", heaterPWM, fanState ? "ON" : "OFF");

        if (heaterPWM > 100) digitalWrite(PIN_ONBOARD_LED, HIGH);
        else digitalWrite(PIN_ONBOARD_LED, LOW);

        lastPrint = millis();
    }
}