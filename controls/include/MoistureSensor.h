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
    // TODO: Tune these during testing!
    int airValue = 3400;   // Raw reading when completely dry in the air
    int waterValue = 1200; // Raw reading when submerged to the line in water
};

#endif