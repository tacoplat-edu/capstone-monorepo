#ifndef LIGHT_CONTROL_H
#define LIGHT_CONTROL_H

#include <Arduino.h>
#include "Config.h"

class LightingControl {
public:
    void setup();
    void loop(); // Checks time

private:
    bool lightsOn = false;
};

#endif
