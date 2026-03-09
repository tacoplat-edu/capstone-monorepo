#ifndef POWER_MONITOR_H
#define POWER_MONITOR_H

#include <Arduino.h>
#include <Adafruit_INA219.h>

class PowerMonitor {
public:
    // Construct with I2C address and actual shunt resistance in ohms
    PowerMonitor(uint8_t addr = 0x40, float shuntResistanceOhms = 0.1f);

    void setup();
    float getVoltage_V();       // Bus voltage in volts
    float getShuntVoltage_mV(); // Raw shunt voltage in millivolts
    float getCurrent_mA();      // Current in milliamps  (computed from shunt voltage / R)
    float getPower_mW();        // Power in milliwatts   (bus voltage * current)

private:
    Adafruit_INA219 ina219;
    uint8_t i2cAddr;            // Stored for debug logging
    float shuntR;               // Actual shunt resistance in ohms
    bool initialized = false;
};

#endif
