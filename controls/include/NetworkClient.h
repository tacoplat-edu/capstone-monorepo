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
    float power_mw;
};

struct SystemTargets {
    float targetTemp;
    // float targetHumidity; // Add these as you expand the PID controllers
    bool triggerWatering; 
};

struct DemoState {
    bool demo_enabled = false;
    bool low_power_mode = false;
    bool heater = false;
    bool water_pump = false;
    bool nutrient_mixer = false;
    bool grow_lights = false;
};

class NetworkClient {
    public:
        void setup();
        void fetchReferenceValues(SystemTargets &targets); 
        void sendTelemetryData(SensorData data);
        void fetchDemoControl(DemoState &state);
    
    private:
        void updateEndpoints(); // Helper to rebuild URL strings
        unsigned long lastPollTime = 0;
        unsigned long lastTelemetryTime = 0;
        unsigned long lastDemoPollTime = 0;
        Preferences preferences; // For non-volatile storage
    };
    
    #endif