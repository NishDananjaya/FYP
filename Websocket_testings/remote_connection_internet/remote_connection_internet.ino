#include <WiFi.h>
#include <WebSocketsClient.h>

const char* ssid = "wifi ssid";
const char* password = "wifi password";

WebSocketsClient webSocket;

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.printf("[WSc] Disconnected, reason: %s\n", payload ? (char*)payload : "Unknown");
      break;
    case WStype_CONNECTED:
      Serial.println("[WSc] Connected to server");
      webSocket.sendTXT("Hello from ESP32!");
      break;
    case WStype_TEXT:
      Serial.printf("[WSc] Received: %s\n", payload);
      break;
    case WStype_ERROR:
      Serial.printf("[WSc] Error: %s\n", payload ? (char*)payload : "Unknown");
      break;
  }
}

void ensureWiFi() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected, reconnecting...");
    WiFi.begin(ssid, password);
    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }
    Serial.println("\nWiFi reconnected");
  }
}

void setup() {
  Serial.begin(115200);
  
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");

  webSocket.beginSSL("domain name of the ngrok tunnel", 443, "/");
  webSocket.onEvent(webSocketEvent);
  webSocket.setReconnectInterval(5000);
}

void loop() {
  ensureWiFi();
  webSocket.loop();
  
  static uint32_t lastTime = 0;
  if (millis() - lastTime > 5000) {
    lastTime = millis();
    webSocket.sendTXT("Ping from ESP32");
  }
}