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
    Serial.println(WiFi.localIP()); // Print IP to confirm network segment
    digitalWrite(PIN_ONBOARD_LED, LOW); 
}

void NetworkClient::pollBackend(SystemTargets &targets) {
    if (millis() - lastPollTime < POLL_INTERVAL_MS) return;
    lastPollTime = millis();

    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient client; // Standard Client for HTTP
        HTTPClient http;
        
        // Pass the standard client into .begin()
        if (http.begin(client, API_ENDPOINT)) { 
            Serial.println("NET: Polling Backend...");
            int httpCode = http.GET();

            if (httpCode > 0) {
                String payload = http.getString();
                Serial.println("NET: Received: " + payload);
                // TODO: Parse JSON here if your server returns targets
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

void NetworkClient::sendTelemetry(float currentTemp, bool heaterState, bool fanState, bool isWatering) {
    if (millis() - lastTelemetryTime < TELEMETRY_INTERVAL_MS) return;
    lastTelemetryTime = millis();

    if (WiFi.status() == WL_CONNECTED) {
        WiFiClient client; // Standard Client for HTTP
        HTTPClient http;
        
        if (http.begin(client, API_TELEMETRY)) {
            
            // Format JSON: {"temperature": 24.5, "heater": true, "fan": false, "watering": false}
            // Note: Using "true"/"false" instead of 1/0 is often safer for JSON parsers
            String jsonPayload = "{";
            jsonPayload += "\"temperature\": " + String(currentTemp) + ",";
            jsonPayload += "\"heater\": " + String(heaterState ? "true" : "false") + ",";
            jsonPayload += "\"fan\": " + String(fanState ? "true" : "false") + ",";
            jsonPayload += "\"watering\": " + String(isWatering ? "true" : "false");
            jsonPayload += "}";

            http.addHeader("Content-Type", "application/json");

            Serial.println("NET: Sending Telemetry -> " + jsonPayload);
            int httpResponseCode = http.POST(jsonPayload);

            if (httpResponseCode > 0) {
                String response = http.getString();
                Serial.print("NET: Telemetry Sent. Response: ");
                Serial.println(httpResponseCode); 
                // Print response body if useful for debugging
                // Serial.println(response);
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