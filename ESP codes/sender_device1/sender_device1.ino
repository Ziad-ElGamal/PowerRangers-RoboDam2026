#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <esp_system.h>
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

// Relay States
#define RELAY_ON  LOW
#define RELAY_OFF HIGH

// OLED Display Config
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

// Receiver Hub MAC Address
uint8_t hubMacAddress[] = {0xA0, 0xA3, 0xB3, 0x27, 0xF7, 0xF4};

typedef struct struct_message {
  char id[16];
  float voltage;
  float current;
  float power;
  bool isOverloaded; 
} struct_message;

typedef struct command_message {
  char id[16];
  bool relay_on;
} command_message;

struct_message myData;
esp_now_peer_info_t peerInfo;

// State Variables
bool overloaded = false;
bool manualRelayState = false;
bool relayOutputOn = false;
unsigned long lastRelayChange = 0;
const unsigned long RELAY_MIN_SWITCH_INTERVAL_MS = 1000;
unsigned long lastSendTime = 0;
unsigned long lastAlarmToggle = 0;
bool alarmState = false;

// NEW: Timer to prevent random noise from tripping the relay
unsigned long overloadStartTime = 0; 

void applyRelayOutput(bool shouldTurnOn) {
  if (shouldTurnOn == relayOutputOn) return;

  unsigned long now = millis();
  if (now - lastRelayChange < RELAY_MIN_SWITCH_INTERVAL_MS) return;

  digitalWrite(PIN_RELAY, shouldTurnOn ? RELAY_ON : RELAY_OFF);
  relayOutputOn = shouldTurnOn;
  lastRelayChange = now;
  Serial.printf("Relay output changed to %s\n", shouldTurnOn ? "ON" : "OFF");
}

void OnDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {}

void OnCommandRecv(const esp_now_recv_info *info, const uint8_t *incomingDataPtr, int len) {
  if (memcmp(info->src_addr, hubMacAddress, 6) != 0) {
    Serial.println("Ignored command from an unknown ESP-NOW sender");
    return;
  }

  if (len == sizeof(command_message)) {
    command_message cmd;
    memcpy(&cmd, incomingDataPtr, sizeof(cmd));
    cmd.id[sizeof(cmd.id) - 1] = '\0';
    if (strcmp(cmd.id, NODE_ID) == 0) {
      Serial.printf("Command received! Dashboard requested Relay %s\n", cmd.relay_on ? "ON" : "OFF");
      manualRelayState = cmd.relay_on;

      // Turning back on is an explicit acknowledgement/reset of a latched trip.
      if (cmd.relay_on) {
        overloaded = false;
        overloadStartTime = 0;
        Serial.println("Overload latch reset by dashboard command");
      }
    }
  }
}

// --- NO-DIVIDER TRUE RMS MATH ---
void readAC_Sensors(float &rmsVoltage, float &rmsCurrent) {
  double sum_v = 0, sum_i = 0;
  double sum_sq_v = 0, sum_sq_i = 0;
  int count = 0;
  
  uint32_t start_time = millis();
  
  // Sample continuously for 50 milliseconds
  while((millis() - start_time) < 50) {
    double read_v = analogRead(PIN_VOLTAGE_SENSOR);
    double read_i = analogRead(PIN_CURRENT_SENSOR);
    
    sum_v += read_v;
    sum_i += read_i;
    sum_sq_v += (read_v * read_v);
    sum_sq_i += (read_i * read_i);
    count++;
  }

  // Prevent divide-by-zero if loop fails
  if (count == 0) return; 

  // Calculate the Mean (Average) to find the DC offset
  double avg_v = sum_v / count;
  double avg_i = sum_i / count;
  
  // Calculate Variance to find the true AC wave amplitude
  double var_v = (sum_sq_v / count) - (avg_v * avg_v);
  double var_i = (sum_sq_i / count) - (avg_i * avg_i);
  
  // Get RMS ADC values
  float rms_v_adc = var_v > 0 ? sqrt(var_v) : 0;
  float rms_i_adc = var_i > 0 ? sqrt(var_i) : 0;

  // Direct conversion to Sensor Voltage (No 1.5x multiplier)
  float rms_v_sensor = (rms_v_adc / 4095.0) * 3.3;
  float rms_i_sensor = (rms_i_adc / 4095.0) * 3.3;

  // CALIBRATION
  float voltageCalibration = 586.0; // Scaled down from 720.0 to fix the 270V reading
  rmsVoltage = rms_v_sensor * voltageCalibration;
  rmsCurrent = rms_i_sensor / 0.066; 

  // ADJUSTED DEADBAND
  if(rmsVoltage < 15.0) rmsVoltage = 0.0;
  if(rmsCurrent < 0.08) rmsCurrent = 0.0; // Lowered to 0.15A (~33W) to detect smaller loads
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
  Serial.printf("Node booted. Reset reason: %d\n", esp_reset_reason());

  pinMode(PIN_RELAY, OUTPUT);
  pinMode(PIN_BUZZER, OUTPUT);
  pinMode(PIN_LED, OUTPUT);
  
  // Fail safe: keep the appliance disconnected until setup succeeds.
  digitalWrite(PIN_RELAY, RELAY_OFF);
  relayOutputOn = false;
  lastRelayChange = millis();
  digitalWrite(PIN_BUZZER, LOW);
  digitalWrite(PIN_LED, LOW);

  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println("OLED init failed");
  }
  display.clearDisplay();

  WiFi.mode(WIFI_STA);
  
  // NEW: Automatically scan for the router and copy its channel
  Serial.println("Scanning for router channel...");
  int16_t networkCount = WiFi.scanNetworks();
  int hubChannel = 1; // Fallback channel
  
  for (int i = 0; i < networkCount; i++) {
    if (WiFi.SSID(i) == "Orange_Guest") { 
      hubChannel = WiFi.channel(i);
      break;
    }
  }
  
  esp_wifi_set_channel(hubChannel, WIFI_SECOND_CHAN_NONE);
  Serial.printf("Node automatically locked to Channel: %d\n", hubChannel);
  
  if (esp_now_init() != ESP_OK) {
    Serial.println("ESP-NOW Init Error");
    return;
  }

  esp_now_register_send_cb(OnDataSent);
  esp_now_register_recv_cb(OnCommandRecv); 

  memcpy(peerInfo.peer_addr, hubMacAddress, 6);
  peerInfo.channel = 0; 
  peerInfo.encrypt = false;
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add Hub peer");
    return;
  }

  // Remain OFF until the dashboard sends an explicit ON command.
  Serial.println("Node ready. Relay remains OFF until enabled from dashboard.");
}

void loop() {
  if (millis() - lastSendTime >= 1000) {
    float v = 0, i = 0;
    
    readAC_Sensors(v, i);
    float p = v * i;

    // --- NEW: 3-SECOND OVERLOAD DEBOUNCE LOGIC ---
    if (p > POWER_LIMIT) {
      if (overloadStartTime == 0) {
        overloadStartTime = millis(); // Start the timer
      } else if (millis() - overloadStartTime >= 3000) {
        overloaded = true; // Trip the relay ONLY if overloaded for 3 solid seconds
      }
    } else {
      overloadStartTime = 0; // Reset timer instantly if power drops to safe levels
      
      if (p == 0 && manualRelayState == false) {
        overloaded = false; // Reset overload state if dashboard manually turns it off
      }
    }

    // Apply the output only when the desired state changes. This prevents
    // repeated writes and enforces a minimum switching interval.
    applyRelayOutput(manualRelayState && !overloaded);

    updateNodeOLED(v, i, p, overloaded);

    strcpy(myData.id, NODE_ID);
    myData.voltage = v;
    myData.current = i;
    myData.power = p;
    myData.isOverloaded = overloaded;

    esp_now_send(hubMacAddress, (uint8_t *) &myData, sizeof(myData));
    lastSendTime = millis(); 
  }

  // ALARM BLINKING LOGIC
  if (overloaded) {
    if (millis() - lastAlarmToggle > 300) { 
      alarmState = !alarmState; 
      digitalWrite(PIN_BUZZER, alarmState ? HIGH : LOW);
      digitalWrite(PIN_LED, alarmState ? HIGH : LOW);
      lastAlarmToggle = millis();
    }
  } else {
    digitalWrite(PIN_BUZZER, LOW);
    digitalWrite(PIN_LED, LOW);
  }
}
