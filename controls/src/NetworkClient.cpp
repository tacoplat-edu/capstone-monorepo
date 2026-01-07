#include "NetworkClient.h"

void NetworkClient::setup() {
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("NET: Connecting to WiFi");
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
        // Blink LED to show we are trying to connect
        digitalWrite(PIN_ONBOARD_LED, !digitalRead(PIN_ONBOARD_LED));
    }
    Serial.println("\nNET: Connected.");
    digitalWrite(PIN_ONBOARD_LED, LOW); // Off when connected
}

void NetworkClient::pollBackend(SystemTargets &targets) {
    if (millis() - lastPollTime < POLL_INTERVAL_MS) return;
    lastPollTime = millis();

    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        // In reality, you'd likely append an ID, e.g., ?id=plantbox_12
        http.begin(API_ENDPOINT);

        Serial.println("NET: Polling Backend...");
        int httpCode = http.GET();

        if (httpCode > 0) {
            String payload = http.getString();
            Serial.println("NET: Received: " + payload);

            // TODO: Parse JSON here. For now, we simulate receiving new targets.
            // Example simulation:
            // targets.targetTemp = 24.5;
            // targets.triggerWatering = false;
        } else {
            Serial.printf("NET: Error %d\n", httpCode);
        }
        http.end();
    } else {
        Serial.println("NET: WiFi Disconnected");
    }
}
