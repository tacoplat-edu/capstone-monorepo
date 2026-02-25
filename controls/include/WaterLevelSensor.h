// WaterLevelSensor.h
#ifndef WATER_LEVEL_SENSOR_H
#define WATER_LEVEL_SENSOR_H

#include <Arduino.h>
#include <Wire.h>
#include <MS5837.h>

class WaterLevelSensor {
public:
    // Configure these per your tank geometry
    float tankDepthMeters    = 0.30f;   // Total water depth when 100% full
    float sensorOffsetMeters = 0.02f;   // Sensor height above tank bottom

    void setup();
    float getWaterLevelPercent();  // 0–100 %, -1 on error

private:
    MS5837 sensor;
    bool initialized = false;
    float p0_mbar = 1013.25f;     // Baseline air pressure

    void calibrateBaseline();
};

#endif
