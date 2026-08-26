# RoboDam 2026 - Smart Energy & AI Diagnostic System

This repository contains the complete source code for an advanced IoT, ESP32-based wireless energy monitoring, control, and diagnostic system, developed for the RoboDam 2026 competition.

The system utilizes a central Hub and multiple Sender Nodes communicating via the ESP-NOW protocol. It features a Python FastAPI backend, a real-time WebSockets dashboard, Telegram bot integration, and an intelligent safety system that monitors power consumption and automatically cuts off power during an electrical overload.

## 🚀 Key Features

* **Two-Way Wireless Communication:** Utilizes the lightweight ESP-NOW protocol to send high-speed sensor packets from the Nodes to the Hub, and broadcasts remote control commands from the Hub back to the Nodes.
* **True RMS AC & DC Monitoring:** Features precise voltage and current calculations, including Auto-Zero calibration for DC loads (HW-872C) and True RMS wave sampling for AC loads (ZMPT101B & ACS712).
* **Hardware Overload Protection:** Automatically triggers a relay to disconnect the load if the current exceeds safe limits. This hardware safety protocol strictly overrides any manual dashboard commands.
* **Real-Time Web Dashboard:** A responsive HTML/JS interface featuring live Chart.js analytics, real-time node telemetry, interactive remote relay controls, and an AI diagnostic alerts feed driven by WebSockets.
* **Python API & Telegram Bot:** A robust `mock_server.py` backend that polls the ESP32 Hub, routes WebSocket traffic, calculates simulated prepaid energy balances, and runs a Telegram bot for remote mobile alerts and status checks.
* **Visual & Audio Alerts:** Dedicated SSD1306 OLED displays on all nodes and the hub render real-time stats, accompanied by active buzzers and warning LEDs during a "RELAY TRIPPED" state.

## 🏗️ System Architecture

1. **ESP32 Nodes:** Read physical sensors, apply safety logic, control the relay, and send data via ESP-NOW.
2. **ESP32 Hub:** Receives ESP-NOW data, connects to local Wi-Fi, and hosts a local HTTP JSON server (`/data` and `/relay`).
3. **Python Server:** Continuously polls the Hub, processes the data, calculates economics/AI alerts, and broadcasts to the frontend.
4. **Frontend / Bot:** The Web Dashboard and Telegram Bot consume the server data for user interaction.

## 📁 Repository Structure

* `/Hub_ESP_code/` - Contains the receiver/Wi-Fi gateway code for the central ESP32 Hub.
* `/sender_nodes/` - Contains the ESP-NOW transmitter/receiver code for the individual appliance nodes (e.g., AC Lamp, DC Fan).
* `mock_server.py` - The FastAPI Python backend, WebSocket manager, and Telegram Bot script.
* `index.html` / `style.css` / `mock_client.js` - The frontend interactive web dashboard files.

## 🛠️ Hardware Components

* ESP32 Development Boards (1x Hub, up to 2x Nodes)
* SSD1306 I2C OLED Displays
* 5V Relay Modules (Active LOW / Active HIGH)
* Active Buzzers, LEDs, and current-limiting resistors
* **Voltage Sensors:** ZMPT101B (AC Voltage)
* **Current Sensors:** ACS712 (AC Current), HW-872C (DC Current)

## ⚡ Pin Configuration (Standard Node)

| Component | ESP32 Pin |
| --- | --- |
| OLED SDA | 21 |
| OLED SCL | 22 |
| Buzzer | 25 |
| Warning LED | 26 |
| Relay Signal | 27 |
| Current Sensor (OUT) | 34 |
| Voltage Sensor (OUT) | 35 |

## 💻 How to Run the Backend Server

To start the Python bridge connecting the physical ESP32 Hub to the Web Dashboard and Telegram:

1. Ensure Python is installed along with the required libraries (`fastapi`, `uvicorn`, `httpx`, `python-telegram-bot`).
2. Open `mock_server.py` and input your specific Hub IP address and Telegram Bot Token.
3. Run the following command in your terminal:

```bash
python -m uvicorn mock_server:app --host 0.0.0.0 --port 8000

```

4. Double-click `index.html` to open the live dashboard in your web browser.

## 👨‍💻 Author

**Power Rangers Team**
