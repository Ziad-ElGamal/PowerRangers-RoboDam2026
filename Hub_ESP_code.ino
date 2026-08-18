#include <esp_now.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- WIFI & LAPTOP CONFIGURATION ---
const char* wifi_ssid = "Orange B";         // <-- CHANGE THIS
const char* wifi_password = "Basemelgamal2"; // <-- CHANGE THIS
const char* server_url = "http://192.168.1.122:8000/update"; // <-- CHANGE TO YOUR LAPTOP IP

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

typedef struct struct_message {
  char id[16];
  float voltage;
  float current;
  float power;
  bool isOverloaded; 
} struct_message;

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

unsigned long lastUpdateTimer = 0;

void OnDataRecv(const esp_now_recv_info *info, const uint8_t *incomingDataPtr, int len) {
  struct_message packet;
  memcpy(&packet, incomingDataPtr, sizeof(packet));

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

void sendDataToLaptop() {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(server_url);
    http.addHeader("Content-Type", "application/json");

    // Build the JSON payload
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

    // Send HTTP POST request
    int httpResponseCode = http.POST(json);
    
    if (httpResponseCode > 0) {
      Serial.print("Data sent to laptop. Response: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error sending data: ");
      Serial.println(httpResponseCode);
    }
    http.end();
  } else {
    Serial.println("WiFi Disconnected. Cannot send data.");
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
    display.println("Connecting to Wi-Fi...");
    display.display();
  }

  // --- CONNECT TO WI-FI (STATION MODE) ---
  WiFi.mode(WIFI_STA);
  WiFi.begin(wifi_ssid, wifi_password);
  
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  Serial.println("\nWiFi Connected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
  Serial.print("Wi-Fi Channel: ");
  Serial.println(WiFi.channel()); // CRITICAL FOR ESP-NOW!

  // Initialize ESP-NOW
  if (esp_now_init() == ESP_OK) {
    esp_now_register_recv_cb(OnDataRecv);
    Serial.println("ESP-NOW Initialized Successfully");
  } else {
    Serial.println("ESP-NOW Initialization Failed");
  }
}

void loop() {
  // Update OLED and send JSON to laptop every 1 second
  if (millis() - lastUpdateTimer > 1000) {
    updateHubOLED();
    sendDataToLaptop();
    lastUpdateTimer = millis();
  }
}
