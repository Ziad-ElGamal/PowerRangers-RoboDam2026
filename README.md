# RoboDam - Smart Energy & AI Diagnostic System (Power Rangers)

Welcome to the **RoboDam** project! This repository contains the source code for a comprehensive real-time energy monitoring and AI-driven diagnostic system, designed for smart homes and prepaid electricity management.

## 🌟 Overview

The Smart Energy & AI Diagnostic System is designed to provide real-time monitoring of electrical appliances, predict energy consumption, and manage prepaid electricity balances. It integrates custom-built IoT hardware (ESP32 microcontrollers) with a robust Python backend (FastAPI) and an interactive web dashboard. The system also leverages AI models to analyze behavioral patterns, detect anomalies, and provide smart recommendations for energy efficiency.

## 🚀 Key Features

* **Real-Time Telemetry:** Live monitoring of Voltage, Current, and Power for up to 4 connected appliances simultaneously.
* **Prepaid Energy Management:** Tracks remaining credit and provides a predicted time left based on current household load and historical usage.
* **AI Diagnostics & Recommendations:** Built-in AI engine detects anomalies (e.g., unusual spikes, appliance faults) and provides actionable energy-saving recommendations.
* **Overload Protection:** Hardware-level tripping mechanism via relay if an appliance exceeds safe power thresholds (with a 3-second debounce logic).
* **Remote Relay Control:** Switch appliances ON/OFF directly from the web dashboard.
* **Interactive Dashboard:** Beautiful, responsive UI with real-time charts (via Chart.js) showing power consumption and load distribution.
* **Offline Resilience:** The hardware uses ESP-NOW for local device-to-hub communication, ensuring node data is reliably gathered even without continuous internet access.

## 🏗️ System Architecture

The project is divided into two primary subsystems: **IoT Hardware** and the **Dashboard / Backend**.

### 1. IoT Hardware (ESP Codes)
The hardware layer is powered by ESP32/ESP8266 microcontrollers utilizing **ESP-NOW** for low-latency, Wi-Fi-independent local communication.

* **Central Hub (`Hub_ESP_code/`)**: Acts as a gateway. It collects telemetry from the sender nodes via ESP-NOW and exposes an HTTP Web Server to the Python backend. It features an OLED display showing the total power and individual node status.
* **Sender Nodes (`sender_device1/`, `sender_device_DC/`)**: Edge devices connected to appliances. They calculate True RMS voltage and current using ZMPT101B and ACS712 sensors. They broadcast telemetry to the Hub and accept commands to toggle relays. Include local OLEDs for status and audible alarms for overloads.

### 2. Dashboard / Backend (Dashboard)
A modern web stack that processes, stores, and visualizes the telemetry data.

* **Backend (`FastAPI`)**: High-performance Python backend serving API endpoints and WebSocket connections for real-time data streaming.
* **AI & Machine Learning Engine**: Includes modules for behavior profiling (`behavior_profile.py`), anomaly detection (`anomaly_detection.py`), and machine learning predictions (`power_prediction_model.pkl`, `auto_training.py`).
* **Database**: Uses SQLite (`telemetry.db`) to store historical energy usage and billing data.
* **Frontend**: HTML5, CSS3, and JavaScript interface displaying live metrics, system status, and Chart.js graphs.

## 📂 Repository Structure

```
RoboDam Final/
├── Dashboard/                      # Backend and Frontend application
│   ├── ai_engine.py                # Core AI orchestration
│   ├── anomaly_detection.py        # Detection of unusual energy spikes
│   ├── auto_training_manager.py    # Automated ML model retraining
│   ├── behavior_*.py               # User behavioral analysis modules
│   ├── database.py                 # SQLite database interactions
│   ├── main.py                     # FastAPI application entry point
│   ├── index.html                  # Web Dashboard UI
│   ├── final_style.css             # Dashboard styling
│   ├── mock_client.js              # Frontend logic and WebSocket handling
│   └── telemetry.db                # SQLite database (generated at runtime)
│
└── ESP codes/                      # Firmware for microcontrollers
    ├── Hub_ESP_code/               # Code for the Central Hub Gateway
    │   └── Hub_ESP_code.ino
    ├── sender_device1/             # Code for AC Appliance Node 1
    │   └── sender_device1.ino
    └── sender_device_DC/           # Code for DC Appliance Node
        └── sender_device_DC.ino
```

## 🛠️ Hardware Requirements

To replicate the IoT layer, you will need:
* **Microcontrollers:** 2+ ESP32 or ESP8266 development boards.
* **Current Sensor:** ACS712 (or similar).
* **Voltage Sensor:** ZMPT101B AC Voltage Sensor.
* **Actuator:** 5V Relay Module.
* **Displays:** SSD1306 128x64 OLED displays (I2C).
* **Misc:** Breadboards, jumper wires, buzzers, and LEDs.

## 💻 Setup & Installation

### 1. Hardware Firmware Flashing
1. Open the Arduino IDE.
2. Install the necessary libraries via the Library Manager: `esp_now`, `Adafruit GFX`, `Adafruit SSD1306`.
3. Flash `Hub_ESP_code.ino` to your primary ESP32 board. (Make sure to update the Wi-Fi credentials in the code to match your network).
4. Update `hubMacAddress` in `sender_device1.ino` and `sender_device_DC.ino` to match your Hub's MAC address.
5. Flash the sender codes to your other ESP32 boards.

### 2. Backend Environment
1. Ensure you have Python 3.9+ installed.
2. Navigate to the `Dashboard` directory.
3. Install the required dependencies:
   ```bash
   pip install fastapi uvicorn sqlite3 scikit-learn pandas numpy
   # (Depending on your exact environment, install any other missing packages)
   ```
4. Run the backend server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

### 3. Running the Dashboard
* Simply open `index.html` in your web browser, or serve the directory using a simple HTTP server (if not served directly via FastAPI static mounts).
* Ensure the backend is running so the WebSockets can connect and stream real-time data.

## 📝 License
This project is built for the RoboDam Final competition. All rights reserved by the Power Rangers team.
