#ifndef CONFIG_H
#define CONFIG_H

#include <Arduino.h>

// --- Device Identity and Settings ---
extern String DEVICE_ID;
extern String BASE_URL;
extern String API_CONFIG;
extern String API_TELEMETRY;

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