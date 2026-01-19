#include "NetworkClient.h"

void NetworkClient::setup() {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("NET: Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        digitalWrite(PIN_ONBOARD_LED, !digitalRead(PIN_ONBOARD_LED));
    }
    Serial.println("\nNET: Connected.");
    Serial.print("NET: IP Address: ");
    Serial.println(WiFi.localIP()); 
    digitalWrite(PIN_ONBOARD_LED, LOW); 
}

void NetworkClient::fetchReferenceValues(SystemTargets &targets) {
    if (millis() - lastPollTime < POLL_INTERVAL_MS) return;
    lastPollTime = millis();

    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient client;
        HTTPClient http;
        
        // Use the Config endpoint: GET /devices/{id}/config
        if (http.begin(client, API_CONFIG)) { 
            Serial.println("NET: Fetching Reference Values...");
            int httpCode = http.GET();

            if (httpCode > 0) {
                String payload = http.getString();
                Serial.println("NET: Config Received: " + payload);
                
                // TODO: Parse the JSON payload here.
                // The payload will look like: {"hardware_id": "...", "targets": {"air_temp": {"min": 18, "max": 28}...}}
                // You will need a JSON parser (like ArduinoJson) to extract 'targets.air_temp.min/max'.
                
            } else {
                Serial.printf("NET: GET Error: %s\n", http.errorToString(httpCode).c_str());
            }
            http.end();
        } else {
            Serial.println("NET: Unable to connect to server");
        }
    } else {
        Serial.println("NET: WiFi Disconnected");
    }
}

void NetworkClient::sendTelemetryData(SensorData data) {
    if (millis() - lastTelemetryTime < TELEMETRY_INTERVAL_MS) return;
    lastTelemetryTime = millis();

    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient client; 
        HTTPClient http;
        
        if (http.begin(client, API_TELEMETRY)) {
            
            // Construct Nested JSON matching 'TelemetryIn' & 'SensorReadings'
            // {
            //   "device_id": "PlantBox-492",
            //   "sensors": {
            //      "air_temp_c": 24.5,
            //      ...
            //   }
            // }
            
            String jsonPayload = "{";
            jsonPayload += "\"device_id\": \"" + String(DEVICE_ID) + "\",";
            
            jsonPayload += "\"sensors\": {";
            jsonPayload += "\"air_temp_c\": " + String(data.air_temp_c) + ",";
            jsonPayload += "\"humidity_pct\": " + String(data.humidity_pct) + ",";
            jsonPayload += "\"light_intensity_pct\": " + String(data.light_intensity_pct) + ",";
            jsonPayload += "\"water_level_pct\": " + String(data.water_level_pct) + ",";
            jsonPayload += "\"nutrient_a_pct\": " + String(data.nutrient_a_pct) + ",";
            jsonPayload += "\"moisture_pct\": " + String(data.moisture_pct);
            jsonPayload += "}"; 
            
            // Note: 'captured_at' is optional (has default in Python), so we omit it here.
            jsonPayload += "}";

            http.addHeader("Content-Type", "application/json");

            Serial.println("NET: Sending Telemetry -> " + jsonPayload);
            int httpResponseCode = http.POST(jsonPayload);

            if (httpResponseCode > 0) {
                // Serial.print("NET: Telemetry Sent. Code: ");
                // Serial.println(httpResponseCode); 
            } else {
                Serial.print("NET: POST Error: ");
                Serial.println(http.errorToString(httpResponseCode).c_str());
            }

            http.end();
        } else {
            Serial.println("NET: Unable to connect to telemetry server");
        }
    }
}