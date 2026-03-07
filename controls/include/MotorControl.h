#ifndef MOTOR_CONTROL_H
#define MOTOR_CONTROL_H

#include <Arduino.h>
#include "Config.h"

// --- LEDC PWM Configuration ---
// ESP32 LEDC channels: 0-15 available
// Pick a channel not used by other peripherals (e.g., LightingControl)
#define MOTOR_PWM_CHANNEL   0
#define MOTOR_PWM_FREQ      25000   // 25 kHz — good for DC motors (above audible range)
#define MOTOR_PWM_RESOLUTION 8      // 8-bit resolution → duty 0–255

class MotorControl {
public:
    /// Call once in setup() to configure the LEDC PWM channel and attach it to the motor pin.
    void setup(uint8_t pin = PIN_MIXER_MOTOR,
               uint8_t channel = MOTOR_PWM_CHANNEL,
               uint32_t freq = MOTOR_PWM_FREQ,
               uint8_t resolution = MOTOR_PWM_RESOLUTION);

    /// Set motor speed via PWM duty cycle.
    /// @param dutyCycle 0 (stopped) – 255 (full speed) when using 8-bit resolution.
    void setSpeed(uint8_t dutyCycle);

    /// Convenience: spin motor at a given speed for a duration, then stop.
    /// @param dutyCycle  PWM duty 0–255
    /// @param durationMs how long to run (blocking)
    void spinFor(uint8_t dutyCycle, unsigned long durationMs);

    /// Stop the motor (duty = 0).
    void stop();

    /// Get the current duty cycle value.
    uint8_t getSpeed() const { return _currentDuty; }

private:
    uint8_t _pin        = PIN_MIXER_MOTOR;
    uint8_t _channel    = MOTOR_PWM_CHANNEL;
    uint8_t _resolution = MOTOR_PWM_RESOLUTION;
    uint8_t _currentDuty = 0;
};

#endif
