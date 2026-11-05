#include <Arduino.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <WiFi.h>

#include "StatusLight.h"
#include "secrets.h"

namespace {
constexpr char kHostname[] = "status-light";
constexpr unsigned long kWifiReconnectIntervalMs = 10000;
constexpr unsigned long kMdnsRetryIntervalMs = 5000;

StatusLight statusLight;
WebServer server(80);
unsigned long lastWifiAttempt = 0;
unsigned long lastMdnsAttempt = 0;
bool wifiConnected = false;
bool mdnsStarted = false;

void sendState() {
    server.send(200, "application/json",
                String("{\"state\":\"") + statusLight.stateName() + "\"}");
}

void sendError(int code, const char* message) {
    server.send(code, "application/json", String("{\"error\":\"") + message + "\"}");
}

bool parseStateJson(const String& body, StatusState& state) {
    const int keyPosition = body.indexOf("\"state\"");
    if (keyPosition < 0) {
        return false;
    }
    const int colonPosition = body.indexOf(':', keyPosition + 7);
    if (colonPosition < 0) {
        return false;
    }

    int position = colonPosition + 1;
    while (position < static_cast<int>(body.length())) {
        const char character = body.charAt(position);
        if (character != ' ' && character != '\t' && character != '\r' && character != '\n') {
            break;
        }
        ++position;
    }
    if (position >= static_cast<int>(body.length()) || body.charAt(position) != '"') {
        return false;
    }

    const int valuePosition = position + 1;
    const int valueEnd = body.indexOf('"', valuePosition);
    if (valueEnd < 0) {
        return false;
    }
    const String value = body.substring(valuePosition, valueEnd);
    return parseStatusState(value.c_str(), state);
}

void handleStatusPost() {
    StatusState state;
    if (!server.hasArg("plain") || !parseStateJson(server.arg("plain"), state)) {
        sendError(400, "expected a JSON state of free, busy, or call");
        return;
    }
    statusLight.setState(state);
    sendState();
}

void handleHealth() {
    server.send(200, "application/json",
                String("{\"ok\":true,\"state\":\"") + statusLight.stateName() + "\"}");
}

void maintainMdns() {
    if (mdnsStarted) {
        return;
    }
    const unsigned long now = millis();
    if (lastMdnsAttempt != 0 && now - lastMdnsAttempt < kMdnsRetryIntervalMs) {
        return;
    }
    lastMdnsAttempt = now;
    if (!MDNS.begin(kHostname)) {
        Serial.println("mDNS start failed");
        return;
    }
    MDNS.addService("http", "tcp", 80);
    mdnsStarted = true;
    Serial.println("mDNS available at http://status-light.local");
}

void maintainWifi() {
    if (WiFi.status() == WL_CONNECTED) {
        if (!wifiConnected) {
            wifiConnected = true;
            Serial.print("Wi-Fi connected; IP address: ");
            Serial.println(WiFi.localIP());
        }
        maintainMdns();
        return;
    }

    if (wifiConnected) {
        Serial.println("Wi-Fi disconnected");
        wifiConnected = false;
    }
    if (mdnsStarted) {
        MDNS.end();
        mdnsStarted = false;
    }
    lastMdnsAttempt = 0;

    const unsigned long now = millis();
    if (lastWifiAttempt != 0 && now - lastWifiAttempt < kWifiReconnectIntervalMs) {
        return;
    }
    lastWifiAttempt = now;
    Serial.println("Connecting to Wi-Fi");
    WiFi.begin(kWifiSsid, kWifiPassword);
}
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    statusLight.begin();

    WiFi.persistent(false);
    WiFi.mode(WIFI_STA);
    WiFi.setHostname(kHostname);
    WiFi.setAutoReconnect(true);

    server.on("/status", HTTP_GET, []() { sendState(); });
    server.on("/status", HTTP_POST, handleStatusPost);
    server.on("/health", HTTP_GET, handleHealth);
    server.onNotFound([]() { sendError(404, "not found"); });
    server.begin();
    Serial.println("HTTP server started");

    maintainWifi();
}

void loop() {
    maintainWifi();
    server.handleClient();
}
