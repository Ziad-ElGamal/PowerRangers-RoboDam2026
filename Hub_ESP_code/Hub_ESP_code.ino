#include <esp_now.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- ROUTER WI-FI CREDENTIALS ---
const char* ssid = "";          // Wi-Fi Name
const char* password = "";  // Wi-Fi Password

WebServer server(80);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Match the exact struct from the Node (Incoming Data)
typedef struct struct_message {
  char id[16];
  float voltage;
  float current;
  float power;
  bool isOverloaded;
} struct_message;

// Structure for sending commands OUT to the nodes
typedef struct command_message {
  char id[16];
  bool relay_on;
} command_message;

// Universal broadcast address for ESP-NOW
uint8_t broadcastAddress[] = {0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF};

struct NodeRecord {
  char id[16];
  float v;
  float a;
  float w;
  bool overloaded;
  unsigned long lastSeen;
  bool active;
};

NodeRecord nodes[4] = {
  {"node_1", 0, 0, 0, false, 0, false},
  {"node_2", 0, 0, 0, false, 0, false},
  {"node_3", 0, 0, 0, false, 0, false},
  {"node_4", 0, 0, 0, false, 0, false}
};

unsigned long lastOledTimer = 0;

// ESP-NOW Receive Callback
void OnDataRecv(const esp_now_recv_info *info, const uint8_t *incomingDataPtr, int len) {
  struct_message packet;
  memcpy(&packet, incomingDataPtr, sizeof(packet));

  Serial.print("[ESP-NOW] Received from ");
  Serial.print(packet.id);
  Serial.printf(" -> V: %.1fV | I: %.2fA | P: %.1fW | Trip: %s\n", 
                packet.voltage, packet.current, packet.power, 
                packet.isOverloaded ? "YES" : "NO");

  for (int i = 0; i < 4; i++) {
    if (strcmp(nodes[i].id, packet.id) == 0 || !nodes[i].active) {
      strcpy(nodes[i].id, packet.id);
      nodes[i].v = packet.voltage;
      nodes[i].a = packet.current;
      nodes[i].w = packet.power;
      nodes[i].overloaded = packet.isOverloaded;
      nodes[i].lastSeen = millis();
      nodes[i].active = true;
      break;
    }
  }
}

// Serves JSON to Python laptop when requested
void handleData() {
  String json = "{\"timestamp\":" + String(millis() / 1000) + ",\"nodes\":[";
  bool first = true;
  unsigned long now = millis();

  for (int i = 0; i < 4; i++) {
    if (nodes[i].active && (now - nodes[i].lastSeen < 5000)) {
      if (!first) json += ",";
      json += "{\"id\":\"" + String(nodes[i].id) + "\",\"v\":" + String(nodes[i].v, 1) + 
              ",\"a\":" + String(nodes[i].a, 2) + ",\"w\":" + String(nodes[i].w, 1) + 
              ",\"overloaded\":" + (nodes[i].overloaded ? "true" : "false") + "}";
      first = false;
    }
  }
  json += "]}";

  server.send(200, "application/json", json);
}

// Catches the HTTP request from Python and broadcasts it via ESP-NOW
void handleRelayCommand() {
  if (server.hasArg("id") && server.hasArg("state")) {
    String targetId = server.arg("id");
    bool turn_on = (server.arg("state") == "1");
    
    command_message cmd;
    targetId.toCharArray(cmd.id, 16);
    cmd.relay_on = turn_on;
    
    // Broadcast the command to all nodes
    esp_now_send(broadcastAddress, (uint8_t *) &cmd, sizeof(cmd));
    
    Serial.printf("[HTTP] Relay command sent to %s: %s\n", cmd.id, turn_on ? "ON" : "OFF");
    server.send(200, "application/json", "{\"status\":\"success\"}");
  } else {
    server.send(400, "application/json", "{\"status\":\"error\"}");
  }
}

void updateHubOLED() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);

  // Show IP and Wi-Fi Channel
  display.setCursor(0, 0);
  display.print("IP: ");
  display.print(WiFi.localIP());
  display.setCursor(100, 0);
  display.print("CH:");
  display.println(WiFi.channel());
  display.drawFastHLine(0, 9, 128, SSD1306_WHITE);

  float totalPower = 0;
  unsigned long now = millis();
  for (int i = 0; i < 4; i++) {
    if (nodes[i].active && (now - nodes[i].lastSeen < 5000)) {
      totalPower += nodes[i].w;
    }
  }

  display.setCursor(0, 13);
  display.print("TOTAL: ");
  display.print(totalPower, 1);
  display.println("W");
  display.drawFastHLine(0, 23, 128, SSD1306_WHITE);

  int yPosition = 27;
  for (int i = 0; i < 4; i++) {
    display.setCursor(0, yPosition);
    if (nodes[i].active && (now - nodes[i].lastSeen < 5000)) {
      if (nodes[i].overloaded) {
        display.printf("%s: ! TRIPPED !", nodes[i].id);
      } else {
        display.printf("%s: %.1fW", nodes[i].id, nodes[i].w);
      }
    } else {
      display.printf("Node %d: OFFLINE", i + 1);
    }
    yPosition += 9;
  }

  display.display();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  if (display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(0, 20);
    display.println("Connecting Wi-Fi...");
    display.display();
  }

  WiFi.disconnect(true);
  delay(500);
  WiFi.persistent(false);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi Connected!");
  Serial.print("Hub IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Wi-Fi Channel: ");
  Serial.println(WiFi.channel());

  // Initialize ESP-NOW
  if (esp_now_init() == ESP_OK) {
    Serial.println("[ESP-NOW] Initialized successfully.");
    esp_now_register_recv_cb(OnDataRecv);
    
    // Register the broadcast peer to send relay commands
    esp_now_peer_info_t peerInfo = {};
    memcpy(peerInfo.peer_addr, broadcastAddress, 6);
    peerInfo.channel = WiFi.channel();  
    peerInfo.encrypt = false;
    
    if (esp_now_add_peer(&peerInfo) != ESP_OK) {
      Serial.println("[ESP-NOW] Failed to add broadcast peer");
    }
  } else {
    Serial.println("[ESP-NOW] Initialization Failed!");
  }

  // Start HTTP Server routes
  server.on("/data", handleData);
  server.on("/relay", handleRelayCommand);
  
  server.begin();
  Serial.println("[HTTP Server] Listening on port 80");
}

void loop() {
  server.handleClient();

  if (millis() - lastOledTimer > 1000) {
    updateHubOLED();
    lastOledTimer = millis();
  }
}
