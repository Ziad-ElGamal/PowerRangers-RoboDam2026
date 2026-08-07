#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- NODE CONFIGURATION ---
const char NODE_ID[16] = "Heater"; // Change to "node_2", "node_3", "node_4" for other nodes
const float SAFE_CURRENT_LIMIT = 10.0; // Current limit in Amps to trigger overload protection

// Hardware Pins Configuration
#define OLED_SDA 21
#define OLED_SCL 22
#define PIN_BUZZER 25
#define PIN_LED 26
#define PIN_RELAY 27 // Active HIGH or LOW depending on relay module (LOW = Disconnect)

// OLED Display Config
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Receiver Hub MAC Address: A0:A3:B3:27:F7:F4
uint8_t hubMacAddress[] = {0xA0, 0xA3, 0xB3, 0x27, 0xF7, 0xF4};

// Shared Packet Structure
typedef struct struct_message {
  char id[16];
  float voltage;
  float current;
  float power;
} struct_message;

struct_message myData;
esp_now_peer_info_t peerInfo;

// ESP-NOW Delivery Callback
void OnDataSent(const wifi_tx_info_t *mac_addr, esp_now_send_status_t status) {
  Serial.print("ESP-NOW Send: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Failed");
}

void updateNodeOLED(float v, float i, float p, bool tripped) {
  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.print("NODE: ");
  display.println(NODE_ID);
  display.drawFastHLine(0, 10, 128, SSD1306_WHITE);

  if (tripped) {
    display.setTextSize(2);
    display.setCursor(0, 22);
    display.println(" OVERLOAD!");
    display.setTextSize(1);
    display.setCursor(0, 48);
    display.println("RELAY TRIPPED!");
  } else {
    display.setTextSize(1);
    display.setCursor(0, 18);
    display.printf("Voltage: %.1f V\n", v);
    display.setCursor(0, 32);
    display.printf("Current: %.2f A\n", i);
    display.setCursor(0, 46);
    display.printf("Power:   %.1f W\n", p);
  }
  
  display.display();
}

void setup() {
  Serial.begin(115200);

  // Initialize Hardware Pins
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  pinMode(PIN_RELAY, OUTPUT);
  
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED, LOW);
  digitalWrite(PIN_RELAY, HIGH); // Closed relay (Power ON)

  // Initialize OLED Screen
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.clearDisplay();

  // Initialize Wireless Network
  WiFi.mode(WIFI_STA);
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW Init Error");
    return;
  }

  esp_now_register_send_cb(OnDataSent);

  // Pair with Central Hub
  memcpy(peerInfo.peer_addr, hubMacAddress, 6);
  peerInfo.channel = 0;
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add Hub peer");
  }
}

void loop() {
  // 1. Read / Calculate Electrical Measurements
  float voltage = 240.0; // Simulated Voltage
  float current = 4.0;  // Simulated Current in Amps
  float power = voltage * current;

  // 2. Overload Protection Check
  bool isOverloaded = (current > SAFE_CURRENT_LIMIT);
  if (isOverloaded) {
    digitalWrite(PIN_BUZZER, HIGH); // Sound Alarm
    digitalWrite(PIN_LED, HIGH);    // Warning Light
    digitalWrite(PIN_RELAY, LOW);   // Open Relay (Disconnect Load)
  } else {
    digitalWrite(PIN_BUZZER, LOW);
    digitalWrite(PIN_LED, LOW);
    digitalWrite(PIN_RELAY, HIGH);
  }

  // 3. Render OLED
  updateNodeOLED(voltage, current, power, isOverloaded);

  // 4. Pack & Send Packet via ESP-NOW
  strcpy(myData.id, NODE_ID);
  myData.voltage = voltage;
  myData.current = current;
  myData.power = power;

  esp_now_send(hubMacAddress, (uint8_t *)&myData, sizeof(myData));

  delay(1000); // 1 Second interval
}