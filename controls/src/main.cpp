// ============================================================
// PUMP TEST: AD20P-1230A on PIN_PUMP_WATER (GPIO 14)
// Turns the pump ON for 3 seconds, then OFF for 3 seconds.
// ============================================================
#include <Arduino.h>
#include "Config.h"

void setup() {
    Serial.begin(SERIAL_BAUD);
    pinMode(PIN_PUMP_WATER, OUTPUT);
    digitalWrite(PIN_PUMP_WATER, LOW);
    delay(1000);
    Serial.println("--- PUMP TEST: AD20P-1230A ---");
}

void loop() {
    Serial.println("PUMP ON");
    digitalWrite(PIN_PUMP_WATER, HIGH);
    delay(3000);

    Serial.println("PUMP OFF");
    digitalWrite(PIN_PUMP_WATER, LOW);
    delay(3000);
}

// ============================================================
// ORIGINAL PLANTBOX FIRMWARE (commented out for pump testing)
// ============================================================


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