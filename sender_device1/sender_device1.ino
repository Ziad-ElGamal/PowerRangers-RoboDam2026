#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// --- NODE CONFIGURATION ---
const char NODE_ID[16] = "lamp"; 
const float POWER_LIMIT = 500.0; // Power limit in Watts for the AC lamp

// Hardware Pins Configuration
#define PIN_CURRENT_SENSOR 34 // ACS712
#define PIN_VOLTAGE_SENSOR 35 // ZMPT101B
#define PIN_BUZZER         25
#define PIN_LED            26
#define PIN_RELAY          27

// Relay States (Adjust if your relay module is active HIGH)
#define RELAY_ON  LOW
#define RELAY_OFF HIGH

// OLED Display Config
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Receiver Hub MAC Address (Using the explicit MAC from your Node 3 code)
uint8_t hubMacAddress[] = {0xA0, 0xA3, 0xB3, 0x27, 0xF7, 0xF4};

// Shared Packet Structure (Sending to Hub)
typedef struct struct_message {
  char id[16];
  float voltage;
  float current;
  float power;
  bool isOverloaded; 
} struct_message;

// Command Structure (Receiving from Hub)
typedef struct command_message {
  char id[16];
  bool relay_on;
} command_message;

struct_message myData;
esp_now_peer_info_t peerInfo;

// Variables for State and Multitasking
bool overloaded = false;
bool manualRelayState = true; // Tracks the ON/OFF state sent from the dashboard
unsigned long lastSendTime = 0;
unsigned long lastAlarmToggle = 0;
bool alarmState = false;

// --- ESP-NOW CALLBACKS ---

void OnDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  // Optional: Uncomment for debugging
  // Serial.print("ESP-NOW Send: ");
  // Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Success" : "Failed");
}

// Listens for relay commands coming from the Hub
void OnCommandRecv(const esp_now_recv_info *info, const uint8_t *incomingDataPtr, int len) {
  if (len == sizeof(command_message)) {
    command_message cmd;
    memcpy(&cmd, incomingDataPtr, sizeof(cmd));
    
    // Check if the Hub is talking to THIS specific node
    if (strcmp(cmd.id, NODE_ID) == 0) {
      Serial.printf("Command received! Dashboard requested Relay %s\n", cmd.relay_on ? "ON" : "OFF");
      manualRelayState = cmd.relay_on; // Update our target state
    }
  }
}

// --- AC RMS MEASUREMENT MATH ---
// Samples the AC wave and calculates true RMS, factoring in your 1k/2k voltage divider.
void readAC_Sensors(float &rmsVoltage, float &rmsCurrent) {
  int max_v = 0, min_v = 4095;
  int max_i = 0, min_i = 4095;
  
  uint32_t start_time = millis();
  
  // Sample the wave for 50 milliseconds
  while((millis() - start_time) < 50) {
    int read_v = analogRead(PIN_VOLTAGE_SENSOR);
    int read_i = analogRead(PIN_CURRENT_SENSOR);
    
    if(read_v > max_v) max_v = read_v;
    if(read_v < min_v) min_v = read_v;
    
    if(read_i > max_i) max_i = read_i;
    if(read_i < min_i) min_i = read_i;
  }

  // Calculate Peak-to-Peak ADC values
  float p2p_v_adc = max_v - min_v;
  float p2p_i_adc = max_i - min_i;

  // Convert ADC back to Voltage at the ESP32 pin
  float p2p_v_pin = (p2p_v_adc / 4095.0) * 3.3;
  float p2p_i_pin = (p2p_i_adc / 4095.0) * 3.3;

  // Reverse the 1k/2k voltage divider 
  float p2p_v_sensor = p2p_v_pin * 1.5;
  float p2p_i_sensor = p2p_i_pin * 1.5;

  // Convert Peak-to-Peak to true RMS
  float rms_v_sensor = (p2p_v_sensor / 2.0) * 0.707;
  float rms_i_sensor = (p2p_i_sensor / 2.0) * 0.707;

  // CALIBRATION (Adjust this to match your wall voltage)
  float voltageCalibration = 480.0; 
  rmsVoltage = rms_v_sensor * voltageCalibration;
  rmsCurrent = rms_i_sensor / 0.066; // ACS712 30A module

  if(rmsVoltage < 20.0) rmsVoltage = 0;
  if(rmsCurrent < 0.15) rmsCurrent = 0;
}

// --- DISPLAY FUNCTION ---
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
    display.printf("Volts: %.1f V\n", v);
    display.setCursor(0, 32);
    display.printf("Amps : %.2f A\n", i);
    display.setCursor(0, 46);
    display.printf("Power: %.1f W\n", p);
  }
  
  display.display();
}

void setup() {
  Serial.begin(115200);

  // Initialize Hardware Pins
  pinMode(PIN_RELAY, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  
  digitalWrite(PIN_RELAY, RELAY_ON);
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED, LOW);

  // Initialize OLED Screen
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.clearDisplay();

  // Initialize Wireless Network (Channel 11 to match Hub)
  WiFi.mode(WIFI_STA);
  esp_wifi_set_channel(11, WIFI_SECOND_CHAN_NONE);
  
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW Init Error");
    return;
  }

  // Register Callbacks
  esp_now_register_send_cb(OnDataSent);
  esp_now_register_recv_cb(OnCommandRecv); // Listen for Hub commands

  // Pair with Central Hub
  memcpy(peerInfo.peer_addr, hubMacAddress, 6);
  peerInfo.channel = 0; // 0 uses the current channel (11)
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add Hub peer");
  }
}

void loop() {
  // --- SENSOR READING & CONTROL LOGIC (Runs exactly once per second) ---
  if (millis() - lastSendTime >= 1000) {
    float v = 0, i = 0;
    
    readAC_Sensors(v, i);
    float p = v * i;

    // Safety Overload Check
    if (p > POWER_LIMIT) {
      overloaded = true;
    } else if (p == 0 && manualRelayState == false) {
      // If the dashboard turned it off, it's not an overload state
      overloaded = false; 
    }

    // Apply Relay Logic
    if (overloaded) {
      digitalWrite(PIN_RELAY, RELAY_OFF); // Cut the power!
    } else {
      if (manualRelayState) {
        digitalWrite(PIN_RELAY, RELAY_ON); // Follow dashboard (ON)
      } else {
        digitalWrite(PIN_RELAY, RELAY_OFF); // Follow dashboard (OFF)
      }
    }

    // Render OLED
    updateNodeOLED(v, i, p, overloaded);

    // Pack & Send Packet via ESP-NOW
    strcpy(myData.id, NODE_ID);
    myData.voltage = v;
    myData.current = i;
    myData.power = p;
    myData.isOverloaded = overloaded;

    esp_now_send(hubMacAddress, (uint8_t *) &myData, sizeof(myData));
    
    lastSendTime = millis(); 
  }

  // --- ALARM BLINKING LOGIC (Runs continuously without freezing) ---
  if (overloaded) {
    if (millis() - lastAlarmToggle > 300) { // Blink every 300 milliseconds
      alarmState = !alarmState; 
      digitalWrite(PIN_BUZZER, alarmState ? HIGH : LOW);
      digitalWrite(PIN_LED, alarmState ? HIGH : LOW);
      lastAlarmToggle = millis();
    }
  } else {
    // Ensure alarms are off when safe
    digitalWrite(PIN_BUZZER, LOW);
    digitalWrite(PIN_LED, LOW);
  }
}
