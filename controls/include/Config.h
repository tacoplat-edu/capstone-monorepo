#ifndef CONFIG_H
#define CONFIG_H

// --- WiFi Credentials ---
inline const char* WIFI_SSID = "BELL198";
inline const char* WIFI_PASS = "39A4F27F563C";

// --- API Endpoints ---
inline const char* API_ENDPOINT = "http://192.168.2.20:8000/health";
inline const char* API_TELEMETRY = "http://192.168.2.20:8000/sendTelemetry";

// --- System Settings ---
#define SERIAL_BAUD 115200
#define POLL_INTERVAL_MS 5000     // How often to check backend
#define TELEMETRY_INTERVAL_MS 10000 // How often to send data (e.g., every 10s)
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