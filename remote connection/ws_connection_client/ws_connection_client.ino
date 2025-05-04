#include <WiFi.h>
#include <WebSocketsClient.h>

const char* ssid = "wifi ssid";
const char* password = "wifi password";


WebSocketsClient webSocket;

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("[WSc] Disconnected");
      break;
    case WStype_CONNECTED:
      Serial.println("[WSc] Connected to server");
      // Send hello message after connecting
      webSocket.sendTXT("Hello from ESP32!");
      break;
    case WStype_TEXT:
      Serial.printf("[WSc] Received: %s\n", payload);
      break;
    default:
      break;
  }
}

void setup() {
  Serial.begin(115200);
  
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }

  Serial.println("Connected to WiFi");

  // Setup WebSocket connection
  webSocket.begin("Pi's Ip address", 8080, "/");

  webSocket.onEvent(webSocketEvent);
}

void loop() {
  webSocket.loop();

  // You can send periodic messages from ESP32
  static uint32_t lastTime = 0;
  if (millis() - lastTime > 5000) {
    lastTime = millis();
    webSocket.sendTXT("Ping from ESP32");
  }
}
