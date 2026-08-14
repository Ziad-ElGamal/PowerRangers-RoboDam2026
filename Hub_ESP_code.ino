#include <esp_now.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

const char* ap_ssid = "RoboDam_Power_Hub"; 
const char* ap_password = "password123";   

WebServer server(80);

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// --- UPDATED: Added isOverloaded boolean ---
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
  bool overloaded; // Tracks the state
  unsigned long lastSeen;
  bool active;
};

// Initialized with the new variable
NodeRecord nodes[4] = {
  {"node_1", 0, 0, 0, false, 0, false},
  {"node_2", 0, 0, 0, false, 0, false},
  {"node_3", 0, 0, 0, false, 0, false},
  {"node_4", 0, 0, 0, false, 0, false}
};

unsigned long lastOledUpdate = 0;

void OnDataRecv(const esp_now_recv_info *info, const uint8_t *incomingDataPtr, int len) {
  struct_message packet;
  memcpy(&packet, incomingDataPtr, sizeof(packet));

  for (int i = 0; i < 4; i++) {
    if (strcmp(nodes[i].id, packet.id) == 0 || !nodes[i].active) {
      strcpy(nodes[i].id, packet.id);
      nodes[i].v = packet.voltage;
      nodes[i].a = packet.current;
      nodes[i].w = packet.power;
      nodes[i].overloaded = packet.isOverloaded; // Save the flag
      nodes[i].lastSeen = millis();
      nodes[i].active = true;
      break;
    }
  }
}

void handleData() {
  String json = "{\"timestamp\":" + String(millis() / 1000) + ",\"nodes\":[";
  bool first = true;
  unsigned long now = millis();

  for (int i = 0; i < 4; i++) {
    if (nodes[i].active && (now - nodes[i].lastSeen < 5000)) {
      if (!first) json += ",";
      // Added overloaded status into the JSON string
      json += "{\"id\":\"" + String(nodes[i].id) + "\",\"v\":" + String(nodes[i].v, 1) + 
              ",\"a\":" + String(nodes[i].a, 2) + ",\"w\":" + String(nodes[i].w, 1) + 
              ",\"overloaded\":" + (nodes[i].overloaded ? "true" : "false") + "}";
      first = false;
    }
  }
  json += "]}";
  server.send(200, "application/json", json);
}

void handleRoot() {
  String html = R"rawliteral(
  <!DOCTYPE HTML>
  <html>
  <head>
    <title>Power Rangers Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body { font-family: 'Segoe UI', sans-serif; background-color: #121212; color: #ffffff; text-align: center; padding: 20px; }
      h1 { color: #00ffcc; }
      .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; margin-top: 30px; }
      .card { background-color: #1e1e1e; border: 1px solid #333; border-radius: 12px; padding: 25px; width: 260px; box-shadow: 0 8px 16px rgba(0,0,0,0.6); transition: 0.3s; }
      .card h2 { margin-top: 0; color: #ffaa00; border-bottom: 1px solid #444; padding-bottom: 10px; }
      .data { font-size: 1.3em; margin: 10px 0; color: #ddd; }
      .power { font-size: 1.8em; font-weight: bold; color: #00ffcc; margin-top: 15px; }
      
      /* --- NEW CSS CLASSES FOR OVERLOAD STATUS --- */
      .card.danger { border: 2px solid #ff4444; background-color: #331111; animation: pulse 1s infinite; }
      .card.danger h2 { color: #ff4444; border-bottom: 1px solid #ff4444; }
      .card.danger .power { color: #ffaa00; }
      .alert-msg { color: #ff4444; font-weight: bold; font-size: 1.2em; margin-bottom: 15px; display: none; }
      .card.danger .alert-msg { display: block; }
      @keyframes pulse { 0% { box-shadow: 0 0 5px #ff4444; } 50% { box-shadow: 0 0 25px #ff4444; } 100% { box-shadow: 0 0 5px #ff4444; } }
    </style>
  </head>
  <body>
    <h1>Power Rangers Energy Dashboard</h1>
    <h3 style="color:#aaa;">RoboDam 2026 - Live System Monitoring</h3>
    <div class="grid" id="nodes-container">
      <p style="color:#888;">Waiting for sensor data...</p>
    </div>
    
    <script>
      setInterval(function() {
        fetch('/data')
          .then(response => response.json())
          .then(data => {
            let html = '';
            if(data.nodes.length === 0) {
              html = '<p style="color:#888;">No active nodes detected.</p>';
            } else {
              data.nodes.forEach(node => {
                // Determine if card needs the danger class
                let cardClass = node.overloaded ? 'card danger' : 'card';
                
                html += `<div class="${cardClass}">
                           <h2>${node.id}</h2>
                           <div class="alert-msg">RELAY TRIPPED</div>
                           <div class="data">Voltage: <b>${node.v} V</b></div>
                           <div class="data">Current: <b>${node.a} A</b></div>
                           <div class="power">${node.w} W</div>
                         </div>`;
              });
            }
            document.getElementById('nodes-container').innerHTML = html;
          })
          .catch(err => console.log("Connection lost"));
      }, 1000);
    </script>
  </body>
  </html>
  )rawliteral";

  server.send(200, "text/html", html);
}

void updateHubOLED() {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);

  display.setCursor(0, 0);
  display.print("IP: ");
  display.println(WiFi.softAPIP());
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
      // Show exclamation mark on Hub OLED if overloaded
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
    display.println("Starting AP Mode...");
    display.display();
  }

  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(ap_ssid, ap_password);

  if (esp_now_init() == ESP_OK) {
    esp_now_register_recv_cb(OnDataRecv);
  }

  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.begin();
}

void loop() {
  server.handleClient();
  if (millis() - lastOledUpdate > 1000) {
    updateHubOLED();
    lastOledUpdate = millis();
  }
}