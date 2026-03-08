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
    void setActuators(int heaterPWM, int fanState);
    
    int getHeaterPWM() { return currentHeaterPWM; }
    bool getFanState() { return currentFanState; }
    float getTemperature();

private:
    int currentHeaterPWM = 0;
    bool currentFanState = false;

    float Kp = 2.0;
    float Ki = 0.5;
    float Kd = 1.0;

    float previousError = 0;
    float integral = 0;
    unsigned long lastTime = 0;
    float maxRateOfChange = 0.5; 

    OneWire* oneWire;
    DallasTemperature* sensors;
};

#endif