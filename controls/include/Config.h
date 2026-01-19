#ifndef CONFIG_H
#define CONFIG_H

// --- Device Identity ---
inline const char* DEVICE_ID = "PlantBox-1"; // Must match a device in your DB

// --- WiFi Credentials ---
inline const char* WIFI_SSID = "BELL198";
inline const char* WIFI_PASS = "39A4F27F563C";

// --- API Endpoints ---
// Ensure your PC and ESP32 are on the same network.
inline const String BASE_URL = "http://192.168.2.20:8000";
inline const String API_CONFIG = BASE_URL + "/devices/" + String(DEVICE_ID) + "/fetchRefVals";
inline const String API_TELEMETRY = BASE_URL + "/sendTelemetry";

// --- System Settings ---
#define SERIAL_BAUD 115200
#define POLL_INTERVAL_MS 5000     
#define TELEMETRY_INTERVAL_MS 10000 
#define CONTROL_LOOP_DELAY_MS 100 

// --- Pin Definitions ---
#define PIN_ONBOARD_LED 2
#define PIN_TEMP_SENSOR 15
#define PIN_HEATER      12
#define PIN_FAN         13
#define PIN_PUMP_WATER     14
#define PIN_PUMP_NUTRIENT  27
#define PIN_VALVE_MAIN     26
#define PIN_MIXER_MOTOR    25
#define PIN_FLOW_SENSOR    33
#define PIN_GROW_LIGHTS    32

#endif