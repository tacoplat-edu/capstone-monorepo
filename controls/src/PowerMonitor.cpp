#include "PowerMonitor.h"
#include "Config.h"

PowerMonitor::PowerMonitor(uint8_t addr, float shuntResistanceOhms)
    : ina219(addr), i2cAddr(addr), shuntR(shuntResistanceOhms) {}

void PowerMonitor::setup() {
    // INA219 uses I2C — Wire.begin() is already called by WaterLevelSensor
    if (!ina219.begin()) {
        Serial.printf("POWER: INA219 @ 0x%02X init failed, check wiring!\n", i2cAddr);
        initialized = false;
        return;
    }

    initialized = true;
    Serial.printf("POWER: INA219 @ 0x%02X Initialized (R_shunt = %.3f ohm)\n", i2cAddr, shuntR);
}

float PowerMonitor::getVoltage_V() {
    if (!initialized) return -1.0f;
    return ina219.getBusVoltage_V();
}

float PowerMonitor::getShuntVoltage_mV() {
    if (!initialized) return -1.0f;
    return ina219.getShuntVoltage_mV();
}

float PowerMonitor::getCurrent_mA() {
    if (!initialized) return -1.0f;
    // Compute from raw shunt voltage and actual shunt resistance
    // shuntVoltage (mV) / resistance (Ω) = current (mA)
    return ina219.getShuntVoltage_mV() / shuntR;
}

float PowerMonitor::getPower_mW() {
    if (!initialized) return -1.0f;
    // power = busVoltage (V) × current (mA) = milliwatts
    float current = getCurrent_mA();
    return ina219.getBusVoltage_V() * current;
}
