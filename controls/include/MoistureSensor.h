#ifndef MOISTURE_SENSOR_H
#define MOISTURE_SENSOR_H

#include <Arduino.h>
#include "Config.h"

class MoistureSensor {
public:
    void setup();
    float getMoisturePercent();

private:
    // Calibration values for ESP32 12-bit ADC (0-4095)
    int airValue = 2495;   
    int waterValue = 700;
};

#endif