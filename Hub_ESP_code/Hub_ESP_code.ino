#include <esp_now.h>
#include <WiFi.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64

// Initialize the OLED display (using I2C)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);

typedef struct struct_message {
  int id;
  float voltage;
  float current;
  float power;
} struct_message;

struct_message myData;

// Flag to tell the loop that new data arrived
volatile bool newData = false; 

// Receive Callback (Keep it as short and fast as possible)
void OnDataRecv(const esp_now_recv_info *info, const uint8_t *incomingData, int len) {
  memcpy(&myData, incomingData, sizeof(myData));
  newData = true; // Tell the main loop to update the screen
}

void setup() {
  Serial.begin(115200);
  
  // Initialize the OLED Screen
  // Address 0x3C is standard for 128x64 I2C OLEDs
  if(!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) {
    Serial.println(F("SSD1306 allocation failed"));
    for(;;); // Loop forever if screen fails to initialize
  }
  
  // Clear the buffer and show a startup message
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(WHITE);
  display.setCursor(0, 20);
  display.println("Waiting for data...");
  display.display();

  // Set device as a Wi-Fi Station
  WiFi.mode(WIFI_STA);

  // Initialize ESP-NOW
  if (esp_now_init() != ESP_OK) {
    Serial.println("Error initializing ESP-NOW");
    return;
  }
  
  // Register the receive callback
  esp_now_register_recv_cb(OnDataRecv);
}

void loop() {
  // If the callback flagged that new data arrived, update the screen
  if (newData) {
    display.clearDisplay();
    
    // Set text size and color
    display.setTextSize(1);
    display.setTextColor(WHITE);
    
    // Display Node ID
    display.setCursor(0, 0);
    display.print("Node ID: ");
    display.println(myData.id);
    
    // Display Voltage
    display.setCursor(0, 16);
    display.print("V: ");
    display.print(myData.voltage);
    display.println(" V");
    
    // Display Current
    display.setCursor(0, 32);
    display.print("I: ");
    display.print(myData.current);
    display.println(" A");
    
    // Display Power
    display.setCursor(0, 48);
    display.print("P: ");
    display.print(myData.power);
    display.println(" W");
    
    // Actually push the graphics to the screen
    display.display();
    
    // Reset the flag until the next packet arrives
    newData = false; 
    
    // Also print to Serial Monitor just in case
    Serial.println("Data updated on OLED!");
  }
}