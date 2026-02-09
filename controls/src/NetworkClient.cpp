#include "NetworkClient.h"

// Define the global config variables (now as mutable Strings)
String DEVICE_ID = "PlantBox-1";
String BASE_URL = "http://192.168.2.20:8000"; 
String API_CONFIG;
String API_TELEMETRY;

void NetworkClient::updateEndpoints() {
    API_CONFIG = BASE_URL + "/devices/" + DEVICE_ID + "/fetchRefVals";
    API_TELEMETRY = BASE_URL + "/sendTelemetry";
}

void NetworkClient::setup() {
    WiFiManager wm;
    preferences.begin("nvs", false); // Open "nvs" namespace in read/write mode

    // 1. Load the last saved Backend IP from memory (default if not found)
    String savedIP = preferences.getString("backend_ip", "192.168.2.20");

    // 2. Add the custom IP field to the Captive Portal
    WiFiManagerParameter custom_backend_ip("server", "Backend IP (e.g. 192.168.2.20)", savedIP.c_str(), 40);
    wm.addParameter(&custom_backend_ip);

    Serial.println("NET: Looking for Wi-Fi...");
    
    // 3. Connect or start Portal
    // If it can't connect, it starts an AP named "PlantBox_Setup"
    if (!wm.autoConnect("PlantBox_Setup")) {
        Serial.println("NET: Failed to connect and hit timeout");
        delay(3000);
        ESP.restart();
    }

    // 4. Save the IP if it was changed in the portal
    String newIP = String(custom_backend_ip.getValue());
    if (newIP != savedIP) {
        preferences.putString("backend_ip", newIP);
        Serial.println("NET: New Backend IP saved to memory.");
    }
    
    BASE_URL = "http://" + newIP + ":8000";
    updateEndpoints();
    preferences.end(); // Close preferences

    Serial.println("NET: Connected & Ready.");
    Serial.println("NET: Backend URL -> " + BASE_URL);
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