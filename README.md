# RoboDam 2026 - Smart Home Energy Monitoring and Monitoring System

This repository contains the source code for an ESP32-based wireless energy monitoring and safety system, developed for the RoboDam 2026 competition. 

The system consists of a central Hub and multiple Sender Nodes communicating via the ESP-NOW protocol to monitor power consumption and automatically cut off power during an electrical overload.

## 🚀 Features
* **Real-Time Monitoring:** Reads simulated/actual voltage (V), current (A), and calculates power (W).
* **Wireless Communication:** Utilizes the lightweight ESP-NOW protocol to send high-speed packets from the Nodes to the central Hub MAC address.
* **Overload Protection:** Automatically triggers a relay to disconnect the load if the current exceeds the safe limit (10.0A).
* **Visual & Audio Alerts:** Features a warning LED, an active buzzer, and a dedicated SSD1306 OLED display that renders real-time stats and alerts users during a "RELAY TRIPPED" state.

## 📁 Repository Structure
* `/Hub_ESP_code/` - Contains the receiver code for the central ESP32 Hub.
* `/sender_device1/` - Contains the ESP-NOW transmitter code for Node 1.
* `/Sender_device2/` - Contains the ESP-NOW transmitter code for Node 2.
* `/sender_device3/` - Contains the ESP-NOW transmitter code for Node 3.
* `/sender_device4/` - Contains the ESP-NOW transmitter code for Node 4.

## 🛠️ Hardware Components
* ESP32 Development Boards (1x Hub, up to 4x Nodes)
* SSD1306 I2C OLED Displays
* 5V Relay Modules (Active LOW)
* Active Buzzers
* LEDs and current-limiting resistors (220Ω - 330Ω)
* Current/Voltage Sensors for real-world integration.

## ⚡ Pin Configuration (Node)
| Component | ESP32 Pin |
| :--- | :--- |
| OLED SDA | 21 |
| OLED SCL | 22 |
| Buzzer | 25 |
| Warning LED | 26 |
| Relay Signal | 27 |

## 👨‍💻 Author
**Power Rangers Team**
