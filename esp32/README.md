# EchoSense ESP32 Sensing Unit Firmware Guide

## 1. Overview
The ESP32 Sensing Unit acts as the environmental acoustic listener and primary safety input for EchoSense:
- **INMP441 I2S Digital Audio Streaming**: Continuously captures and streams 16 kHz uncompressed digital audio.
- **Physical SOS Emergency Trigger**: Monitored via hardware interrupt on GPIO 18 with 50ms software debounce, automatic active-state polarity detection, and 5-second anti-bounce cooldown.
- **Resilient WebSocket Connection**: Instant status sync, periodic telemetry heartbeats, and non-blocking I2S reading (prevents loop lockup if mic is unpowered).

---

## 2. Hardware Wiring (Standard Conflict-Free Pins)
For complete wiring diagrams and instructions, see **[HARDWARE_SETUP_GUIDE.md](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/HARDWARE_SETUP_GUIDE.md)** or [docs/ESP32_CONNECTIONS.md](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/docs/ESP32_CONNECTIONS.md).

- **INMP441 VDD** -> **3.3V (3V3)** *(Never 5V!)*
- **INMP441 GND & L/R** -> **GND** *(Do NOT leave L/R floating!)*
- **INMP441 SCK (BCLK)** -> **GPIO 14**
- **INMP441 WS (LRCK)** -> **GPIO 25**
- **INMP441 SD (DIN)** -> **GPIO 32**
- **3-Pin SOS Button Module**:
  - **VCC** (or `+`) -> **3.3V (3V3)** *(CRITICAL: NEVER connect to 5V/VIN!)*
  - **GND** (or `-`) -> **GND**
  - **SW1** (or `S`) -> **GPIO 18**
- **Status LED** -> Built-in Blue LED on **GPIO 2**

---

## 3. Recommended: Single-File Unified Upload

Use the single unified sketch file for both ESP32 and ESP8266:
**[`EchoSense_Unified/EchoSense_Unified.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/EchoSense_Unified/EchoSense_Unified.ino)**

### Upload Steps:
1. Open `EchoSense_Unified/EchoSense_Unified.ino` in **Arduino IDE**.
2. Update your Wi-Fi name, password, and laptop IP address at lines 30–36.
3. Plug in your ESP32 board.
4. Select **Tools → Board → esp32 → ESP32 Dev Module** (or your specific ESP32 board).
5. Select your COM Port under **Tools → Port**.
6. Required Libraries: `WebSockets by Markus Sattler`, `ArduinoJson by Benoit Blanchon`.
7. Click **Upload** (➜).
   *(If the console shows `Connecting...`, hold down the BOOT button on the ESP32 for 2 seconds).*
8. Open the Serial Monitor at **115200** baud. You will see:
   ```text
   [I2S] INMP441 Driver Installed.
   ✅ [WiFi] Connected! IP: 192.168.29.xxx
   ✅ [WS] Connected to EchoSense Portal!
   ```
