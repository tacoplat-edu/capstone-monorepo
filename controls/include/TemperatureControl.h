#ifndef TEMP_CONTROL_H
#define TEMP_CONTROL_H

#include <Arduino.h>
#include "Config.h"
#include <OneWire.h>
#include <DallasTemperature.h> 

class TemperatureControl {
public:
    void setup();
    void loop(float currentTemp, float targetTemp);
    
    // Getters for Telemetry
    int getHeaterPWM() { return currentHeaterPWM; }
    bool getFanState() { return currentFanState; }
    float getTemperature();

private:
    // State tracking variables
    int currentHeaterPWM = 0;
    bool currentFanState = false;

    // PID Constants (Need tuning as per report Sec 3.4)
    float Kp = 2.0;
    float Ki = 0.5;
    float Kd = 1.0;

    float previousError = 0;
    float integral = 0;
    unsigned long lastTime = 0;

    // Safety constraints
    float maxRateOfChange = 0.5; // deg C per minute (Report constraint)

    // DS18B20 Sensor (NEW)
    #define ONE_WIRE_BUS 4  // Yellow wire GPIO - CHANGE IF NEEDED
    OneWire* oneWire;
    DallasTemperature* sensors;

    void setActuators(int heaterPWM, int fanState);
};

#endif
