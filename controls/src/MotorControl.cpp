#include "MotorControl.h"

void MotorControl::setup(uint8_t pin, uint8_t channel, uint32_t freq, uint8_t resolution) {
    _pin        = pin;
    _channel    = channel;
    _resolution = resolution;
    _currentDuty = 0;

    // Configure the LEDC timer/channel
    ledcSetup(_channel, freq, _resolution);

    // Attach the channel to the GPIO pin
    ledcAttachPin(_pin, _channel);

    // Start with motor off
    ledcWrite(_channel, 0);

    Serial.printf("MOTOR: PWM initialized on GPIO %d | Channel %d | Freq %d Hz | %d-bit\n",
                  _pin, _channel, freq, _resolution);
}

void MotorControl::setSpeed(uint8_t dutyCycle) {
    _currentDuty = dutyCycle;
    ledcWrite(_channel, _currentDuty);
    Serial.printf("MOTOR: Speed set to %d / %d\n", _currentDuty, (1 << _resolution) - 1);
}

void MotorControl::spinFor(uint8_t dutyCycle, unsigned long durationMs) {
    Serial.printf("MOTOR: Spinning at duty %d for %lu ms\n", dutyCycle, durationMs);
    setSpeed(dutyCycle);
    delay(durationMs);
    stop();
    Serial.println("MOTOR: spinFor complete — motor stopped.");
}

void MotorControl::stop() {
    _currentDuty = 0;
    ledcWrite(_channel, 0);
    Serial.println("MOTOR: Stopped.");
}
