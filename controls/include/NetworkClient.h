#ifndef NETWORK_CLIENT_H
#define NETWORK_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "Config.h"

struct SystemTargets {
    float targetTemp;
    float targetHumidity; // Coupled in report, but separated in controls
    bool triggerWatering; // Backend flag to force watering
};

class NetworkClient {
public:
    void setup();
    void pollBackend(SystemTargets &targets); // Updates the targets by ref

private:
    unsigned long lastPollTime = 0;
};

#endif
