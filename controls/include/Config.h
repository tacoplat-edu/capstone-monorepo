#ifndef CONFIG_H
#define CONFIG_H

// --- WiFi Credentials ---
const char* WIFI_SSID = "";
const char* WIFI_PASS = "";
const char* API_ENDPOINT = "http://your-backend-api.com/status"; // Placeholder

// --- System Settings ---
#define SERIAL_BAUD 115200
#define POLL_INTERVAL_MS 5000     // How often to check backend
#define CONTROL_LOOP_DELAY_MS 100 // How often to run PID/Safety checks

// --- Pin Definitions (Placeholder / Simulation) ---
// Since hardware isn't ready, we use dummy pins or Onboard LED for visual feedback
#define PIN_ONBOARD_LED 2

// Temperature Subsystem
#define PIN_TEMP_SENSOR 15
#define PIN_HEATER      12
#define PIN_FAN         13

// Fluid Subsystem
#define PIN_PUMP_WATER     14
#define PIN_PUMP_NUTRIENT  27
#define PIN_VALVE_MAIN     26
#define PIN_MIXER_MOTOR    25
#define PIN_FLOW_SENSOR    33

// Lighting
#define PIN_GROW_LIGHTS    32

#endif
