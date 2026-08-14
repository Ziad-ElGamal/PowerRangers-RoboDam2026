#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- NODE CONFIGURATION ---
const char NODE_ID[16] = "Fan"; 
const float SAFE_CURRENT_LIMIT = 5.0; // Current limit in Amps to trigger overload protection

// Hardware Pins Configuration
#define OLED_SDA 21
#define OLED_SCL 22
#define PIN_BUZZER 25
#define PIN_LED 26
#define PIN_RELAY 27 // Active LOW relay module
#define PIN_SENSOR 34 // HW-872C OUT pin

// OLED Display Config
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Receiver Hub MAC Address
uint8_t hubMacAddress[] = {0xA0, 0xA3, 0xB3, 0x27, 0xF7, 0xF4};

// Shared Packet Structure
typedef struct struct_message {
  char id[16];
  float voltage;
  float current;
  float power;
  bool isOverloaded; // Added to match Hub packet structure
} struct_message;

struct_message myData;
esp_now_peer_info_t peerInfo;

// Variable to store the sensor's unique resting voltage
float sensorBaseline = 2.5; 

void OnDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
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
  
  // Show startup message on OLED
  display.setCursor(0, 20);
  display.println("Calibrating Sensor...");
  display.display();

  // --- AUTO-ZERO CALIBRATION ---
  // Take 50 quick readings at startup to find the exact resting baseline of your specific 30A module
  float sumVoltage = 0;
  for (int i = 0; i < 50; i++) {
    int raw = analogRead(PIN_SENSOR);
    sumVoltage += (raw / 4095.0) * 3.3;
    delay(10);
  }
  sensorBaseline = sumVoltage / 50.0; // Sets your module's precise factory offset
  // -----------------------------

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
  float voltage = 5.0; // 5V Fan Test Voltage

  // --- CALIBRATED SENSOR MATH ---
  int adcRaw = analogRead(PIN_SENSOR); 
  float pinVoltage = (adcRaw / 4095.0) * 3.3; 

  // Calculate current using your unique calibrated baseline instead of a fixed 2.5V
  float current = (pinVoltage - sensorBaseline) / 0.066;

  // Absolute value
  if (current < 0) {
    current = -current;
  }

  // Filter out minor background noise
  if (current < 0.15) {
    current = 0.0;
  }
  // --- END SENSOR MATH ---

  float power = voltage * current;

  // 2. Overload Protection Check
  bool isOverloaded = (current > SAFE_CURRENT_LIMIT);
  if (isOverloaded) {
    digitalWrite(PIN_RELAY, LOW);   // Open Relay (Disconnect Load)
  } else {
    digitalWrite(PIN_RELAY, HIGH);  // Close Relay (Power ON)
    digitalWrite(PIN_BUZZER, LOW);  // Ensure Buzzer is quiet
    digitalWrite(PIN_LED, LOW);     // Ensure LED is OFF
  }

  // 3. Render OLED
  updateNodeOLED(voltage, current, power, isOverloaded);

  // 4. Pack & Send Packet via ESP-NOW
  strcpy(myData.id, NODE_ID);
  myData.voltage = voltage;
  myData.current = current;
  myData.power = power;
  myData.isOverloaded = isOverloaded; // Added to packet

  esp_now_send(hubMacAddress, (uint8_t *)&myData, sizeof(myData));

  // 5. Smart Delay & Beep Sequence
  if (isOverloaded) {
    for (int b = 0; b < 5; b++) {
      digitalWrite(PIN_BUZZER, HIGH);
      digitalWrite(PIN_LED, HIGH);   
      delay(100);
      digitalWrite(PIN_BUZZER, LOW);
      digitalWrite(PIN_LED, LOW);
      delay(100);
    }
  } else {
    delay(1000); 
  }
}