#ifndef FLUID_CONTROL_H
#define FLUID_CONTROL_H

#include <Arduino.h>
#include "Config.h"

class FluidControl {
public:
    void setup();
    void loop();
    void triggerWateringCycle(); // Called by main when backend requests it
    
    // Getter for Telemetry
    bool isWateringActive() { return isWatering; }

private:
    bool isWatering = false;
    int cycleStep = 0;
    unsigned long stepStartTime = 0;

    void stopAll();
};

#endif