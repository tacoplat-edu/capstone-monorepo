#ifndef NETWORK_CLIENT_H
#define NETWORK_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "Config.h"

struct SystemTargets {
    float targetTemp;
    float targetHumidity; 
    bool triggerWatering; 
};

class NetworkClient {
public:
    void setup();
    void pollBackend(SystemTargets &targets); 
    
    // New function to POST telemetry
    void sendTelemetry(float currentTemp, bool heaterState, bool fanState, bool isWatering);

private:
    unsigned long lastPollTime = 0;
    unsigned long lastTelemetryTime = 0; // Timer for sending data
};

#endif