#include <esp_now.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- YOUR ROUTER WI-FI CREDENTIALS ---
const char* ssid = "Youssef29";         // Replace with your 2.4GHz Wi-Fi Name
const char* password = "@1111/saloma16"; // Replace with your Wi-Fi Password

WebServer server(80);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

typedef struct struct_message {
  char id[16];
  float voltage;
  float current;
  float power;
} struct_message;

struct NodeRecord {
  char id[16];
  float v;
  float a;
  float w;
  unsigned long lastSeen;
  bool active;
};

NodeRecord nodes[4] = {
  {"node_1", 0, 0, 0, 0, false},
  {"node_2", 0, 0, 0, 0, false},
  {"node_3", 0, 0, 0, 0, false},
  {"node_4", 0, 0, 0, 0, false}
};

// ESP-NOW Receive Callback (Receives data from Nodes 1-4)
void OnDataRecv(const esp_now_recv_info *info, const uint8_t *incomingDataPtr, int len) {
  struct_message packet;
  memcpy(&packet, incomingDataPtr, sizeof(packet));

  // Print incoming node packet directly to Serial Monitor
  Serial.print("[ESP-NOW] Received from ");
  Serial.print(packet.id);
  Serial.printf(" --> V: %.1fV | I: %.2fA | P: %.1fW\n", packet.voltage, packet.current, packet.power);

  for (int i = 0; i < 4; i++) {
    if (strcmp(nodes[i].id, packet.id) == 0 || !nodes[i].active) {
      strcpy(nodes[i].id, packet.id);
      nodes[i].v = packet.voltage;
      nodes[i].a = packet.current;
      nodes[i].w = packet.power;
      nodes[i].lastSeen = millis();
      nodes[i].active = true;
      break;
    }
  }
}

// Serves aggregate JSON to PC & prints it to Serial Monitor
void handleData() {
  String json = "{\"timestamp\":" + String(millis() / 1000) + ",\"nodes\":[";
  bool first = true;
  unsigned long now = millis();

  for (int i = 0; i < 4; i++) {
    if (nodes[i].active && (now - nodes[i].lastSeen < 5000)) {
      if (!first) json += ",";
      json += "{\"id\":\"" + String(nodes[i].id) + "\",\"v\":" + String(nodes[i].v, 1) + ",\"a\":" + String(nodes[i].a, 2) + ",\"w\":" + String(nodes[i].w, 1) + "}";
      first = false;
    }
  }
  json += "]}";

  // Print requested JSON payload to Serial Monitor
  Serial.print("[HTTP GET /data] Output Payload: ");
  Serial.println(json);

  server.send(200, "application/json", json);
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== Central Hub Starting ===");

  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 20);
    display.println("Connecting Wi-Fi...");
    display.display();
  }

  // 1. Clean Wi-Fi connection to Router
  WiFi.disconnect(true);
  delay(500);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\n------------------------------------");
  Serial.print("Connected! Hub Assigned IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Wi-Fi Channel: ");
  Serial.println(WiFi.channel());
  Serial.println("------------------------------------");

  // Show IP on Hub Display
  display.clearDisplay();
  display.setCursor(0, 0);
  display.println("HUB ONLINE");
  display.setCursor(0, 20);
  display.print("IP: ");
  display.println(WiFi.localIP());
  display.display();

  // 2. Initialize ESP-NOW to listen for nodes
  if (esp_now_init() == ESP_OK) {
    Serial.println("[ESP-NOW] Initialized successfully.");
    esp_now_register_recv_cb(OnDataRecv);
  } else {
    Serial.println("[ESP-NOW] Initialization Failed!");
  }

  // 3. Start Web Server
  server.on("/data", handleData);
  server.begin();
  Serial.println("[HTTP Server] Listening on port 80");
}

void loop() {
  server.handleClient();
}
