#include <Arduino.h>
#include "Config.h"
#include "NetworkClient.h"
#include "TemperatureControl.h"
#include "FluidControl.h"
#include "LightingControl.h"
#include "WaterLevelSensor.h"
#include "MoistureSensor.h" 

// --- Global Objects ---
NetworkClient network;
TemperatureControl tempControl;
FluidControl fluidControl;
LightingControl lightControl;
WaterLevelSensor waterLevelSensor;
MoistureSensor moistureSensor;     

// --- State Variables ---
SystemTargets currentTargets; 
DemoState demoState;

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_ONBOARD_LED, OUTPUT);

    Serial.println("--- PLANTBOX FIRMWARE STARTING ---");

    network.setup();
    tempControl.setup();
    fluidControl.setup();
    lightControl.setup();
    waterLevelSensor.setup();
    moistureSensor.setup();        
    delay(1000); 

    currentTargets.targetTemp = 24.0;
    currentTargets.triggerWatering = false;
}

void loop() {
    network.fetchReferenceValues(currentTargets);
    network.fetchDemoControl(demoState);

    SensorData currentReadings;
    currentReadings.air_temp_c = tempControl.getTemperature(); 
    currentReadings.water_level_pct = waterLevelSensor.getWaterLevelPercent();
    currentReadings.moisture_pct = moistureSensor.getMoisturePercent(); 
    
    // Remaining Placeholders
    currentReadings.humidity_pct = 60.0;        
    currentReadings.light_intensity_pct = 85.0; 
    currentReadings.nutrient_a_pct = 95.0;      

    if (demoState.demo_enabled) {
        // Demo mode: override targets with high values to activate actuators
        tempControl.loop(currentReadings.air_temp_c, 50.0);
        fluidControl.triggerWateringCycle();
    } else {
        // Normal control logic
        tempControl.loop(currentReadings.air_temp_c, currentTargets.targetTemp);
        fluidControl.loop();

        if (currentTargets.triggerWatering) {
            fluidControl.triggerWateringCycle();
            currentTargets.triggerWatering = false; 
        }
    }

    lightControl.loop();

    network.sendTelemetryData(currentReadings);

    delay(CONTROL_LOOP_DELAY_MS);
}





// for testing 3 sensors:
// #include <Arduino.h>
// #include "Config.h"
// #include "TemperatureControl.h"
// #include "WaterLevelSensor.h"
// #include "MoistureSensor.h"

// // Instantiate only the sensors for testing
// TemperatureControl tempControl;
// WaterLevelSensor waterLevelSensor;
// MoistureSensor moistureSensor;

// void setup() {
//     Serial.begin(SERIAL_BAUD);
//     delay(1000);
//     Serial.println("\n--- SENSOR CALIBRATION AND TEST MODE ---");

//     // Initialize sensors
//     tempControl.setup();
//     waterLevelSensor.setup();
//     moistureSensor.setup();
    
//     Serial.println("Setup complete. Starting readings...\n");
// }

// void loop() {
//     Serial.println("----------------------------------------");
    
//     // 1. DS18B20 Temperature
//     float temp = tempControl.getTemperature();
//     Serial.printf("TEMP (DS18B20): %.2f °C\n", temp);

//     // 2. MS5837 Water Level
//     float waterPct = waterLevelSensor.getWaterLevelPercent();
//     Serial.printf("WATER LEVEL (MS5837): %.2f %%\n", waterPct);

//     // 3. EK1940 Soil Moisture
//     int rawMoisture = analogRead(PIN_MOISTURE_SENSOR);
//     float moisturePct = moistureSensor.getMoisturePercent();
//     Serial.printf("MOISTURE (EK1940): Raw ADC = %d | Calculated = %.2f %%\n", rawMoisture, moisturePct);

//     delay(2000); // Wait 2 seconds between readings
// }