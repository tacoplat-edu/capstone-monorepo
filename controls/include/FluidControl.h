#ifndef FLUID_CONTROL_H
#define FLUID_CONTROL_H

#include <Arduino.h>
#include "Config.h"

// --- Mixer Motor PWM Configuration ---
#define MIXER_PWM_CHANNEL    2       // LEDC channel 2 (channels 0-1 share Timer 0 with heater)
#define MIXER_PWM_FREQ       25000   // 25 kHz — above audible range
#define MIXER_PWM_RESOLUTION 8       // 8-bit → duty 0–255

class FluidControl {
public:
    void setup();
    void loop();
    void triggerWateringCycle(); // Called by main when backend requests it

    /// Set mixer motor speed via PWM duty cycle.
    /// @param dutyCycle 0 (stopped) – 255 (full speed)
    void setMixerSpeed(uint8_t dutyCycle);

    /// Stop the mixer motor (duty = 0).
    void stopMixer();

    /// Get the current mixer duty cycle.
    uint8_t getMixerSpeed() const { return _mixerDuty; }

    // Getter for Telemetry
    bool isWateringActive() { return isWatering; }

private:
    bool isWatering = false;
    int cycleStep = 0;
    int prevStep = -1;
    unsigned long stepStartTime = 0;

    // Mixer PWM state
    uint8_t _mixerChannel    = MIXER_PWM_CHANNEL;
    uint8_t _mixerResolution = MIXER_PWM_RESOLUTION;
    uint8_t _mixerDuty       = 0;

    void stopAll();
};

#endif