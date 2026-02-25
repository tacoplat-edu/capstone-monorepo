// WaterLevelSensor.cpp
#include "WaterLevelSensor.h"

void WaterLevelSensor::setup() {
    Wire.begin();

    // Identify correct model (02BA for your module)[web:24]
    sensor.setModel(MS5837::MS5837_02BA);
    if (!sensor.init()) {
        Serial.println("WATER: MS5837 init failed, check wiring!");
        initialized = false;
        return;
    }

    // Fresh water density so depth() uses ~997 kg/m^3[web:1][web:21]
    sensor.setFluidDensity(997);

    initialized = true;
    calibrateBaseline();
}

void WaterLevelSensor::calibrateBaseline() {
    // Optional: average a few readings in air or with tank empty
    Serial.println("WATER: Calibrating baseline pressure (p0)...");
    const int samples = 10;
    float sum = 0.0f;

    for (int i = 0; i < samples; i++) {
        sensor.read();                    // 40 ms typical
        sum += sensor.pressure();         // mbar
        delay(50);
    }

    p0_mbar = sum / samples;
    Serial.print("WATER: p0 = ");
    Serial.print(p0_mbar);
    Serial.println(" mbar");
}

float WaterLevelSensor::getWaterLevelPercent() {
    if (!initialized) return -1.0f;

    sensor.read();                        // update internal values

    // Option A: use depth() directly (uses setFluidDensity + absolute pressure)
    float depthMeters = sensor.depth();   // meters of water above sensor

    // If sensor is above the bottom, add that distance to get effective water column
    depthMeters += sensorOffsetMeters;

    // Clamp to [0, tankDepthMeters]
    if (depthMeters < 0) depthMeters = 0;
    if (depthMeters > tankDepthMeters) depthMeters = tankDepthMeters;

    float pct = (depthMeters / tankDepthMeters) * 100.0f;
    return pct;
}
