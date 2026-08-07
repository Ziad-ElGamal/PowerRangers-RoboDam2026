#include <esp_now.h>
#include <WiFi.h>
#include <esp_wifi.h> // Required for wifi_tx_info_t in ESP32 Core v3.0+

// Central Hub MAC Address: A0:A3:B3:27:F7:F4
uint8_t receiverMacAddress[] = {0xA0, 0xA3, 0xB3, 0x27, 0xF7, 0xF4};

// Structure matching Hub code exactly
typedef struct struct_message {
  char id[32]; // Fixed-size char array for text
  float voltage;
  float current;
  float power;
} struct_message;

struct_message myData;
esp_now_peer_info_t peerInfo;

// CORRECTED Callback function for ESP32 Core v3.0+
void OnDataSent(const wifi_tx_info_t *info, esp_now_send_status_t status) {
  Serial.print("Delivery Status: ");
  Serial.println(status == ESP_NOW_SEND_SUCCESS ? "Delivery Success" : "Delivery Fail");
}

void setup() {
  Serial.begin(115200);

  // Set Wi-Fi mode
  WiFi.mode(WIFI_STA);

  // Init ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }

  // Register send callback
  esp_now_register_send_cb(OnDataSent);

  // Register peer (Receiver Hub)
  memcpy(peerInfo.peer_addr, receiverMacAddress, 6);
  peerInfo.channel = 0;  
  peerInfo.encrypt = false;
  
  if (esp_now_add_peer(&peerInfo) != ESP_OK) {
    Serial.println("Failed to add peer");
    return;
  }
}

void loop() {
  // Use strncpy to securely copy text into the char array
  strncpy(myData.id, "Television", sizeof(myData.id));
                     
  myData.voltage = 240.9;            
  myData.current = 2.0;              
  myData.power = myData.voltage * myData.current; 

  // Send packet via ESP-NOW
  esp_err_t result = esp_now_send(receiverMacAddress, (uint8_t *) &myData, sizeof(myData));
  
  if (result == ESP_OK) {
    Serial.println("Sent packet successfully");
  } else {
    Serial.println("Error sending packet");
  }

  delay(2000); // Send data every 2 seconds
}