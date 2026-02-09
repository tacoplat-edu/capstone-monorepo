#ifndef NETWORK_CLIENT_H
#define NETWORK_CLIENT_H

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include "Config.h"
#include <WiFiManager.h> 
#include <Preferences.h> 

// Mirrors the 'SensorReadings' model in Python
struct SensorData {
    float air_temp_c;
    float humidity_pct;
    float light_intensity_pct;
    float water_level_pct;
    float nutrient_a_pct;
    float moisture_pct;
};

struct SystemTargets {
    float targetTemp;
    // float targetHumidity; // Add these as you expand the PID controllers
    bool triggerWatering; 
};

class NetworkClient {
    public:
        void setup();
        void fetchReferenceValues(SystemTargets &targets); 
        void sendTelemetryData(SensorData data);
    
    private:
        void updateEndpoints(); // Helper to rebuild URL strings
        unsigned long lastPollTime = 0;
        unsigned long lastTelemetryTime = 0; 
        Preferences preferences; // For non-volatile storage
    };
    
    #endif