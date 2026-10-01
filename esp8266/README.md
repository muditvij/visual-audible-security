# EchoSense ESP8266 Alert Unit Firmware Guide

## 1. Overview
The ESP8266 Alert Unit functions as the physical visual and acoustic output for EchoSense:
- **WS2812 NeoPixel RGB Ring**: Clear color coding for ambient sound awareness and high-speed emergency strobe.
- **Acoustic Buzzer**: Multi-pattern alert tones (warning beeps, alarm bursts, urgent SOS alarm).
- **Central Priority Engine**: Ensures lower-priority audio cues cannot overwrite active safety emergencies.
- **Offline Safety Monitoring**: Automatically indicates if the laptop backend hub becomes unreachable.

> [!NOTE]
> The 16-pin LCD display has been completely removed to simplify hardware assembly to only 2 signal wires and prevent any ESP8266 boot-strapping pin lockups. All detailed wave telemetry and event records are visualized on the Web Dashboard.

---

## 2. Hardware Wiring (Standard Conflict-Free Pins)
For complete wiring diagrams and instructions, see **[HARDWARE_SETUP_GUIDE.md](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/HARDWARE_SETUP_GUIDE.md)** or [docs/ESP8266_CONNECTIONS.md](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/docs/ESP8266_CONNECTIONS.md).

- **Buzzer Signal (IP/SIG)** -> **NodeMCU D1 (GPIO 5)**
- **Buzzer VCC** -> **NodeMCU 3V3** (or VIN)
- **Buzzer GND** -> **NodeMCU GND**
- **WS2812 RGB Ring DI** -> **NodeMCU D2 (GPIO 4)**
- **WS2812 5V / VDD** -> **NodeMCU VIN** (5V directly from USB bus — *NEVER 3.3V!*)
- **WS2812 GND** -> **NodeMCU GND**

---

## 3. Recommended: Single-File Unified Upload

Use the single unified sketch file for both ESP32 and ESP8266:
**[`EchoSense_Unified/EchoSense_Unified.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/EchoSense_Unified/EchoSense_Unified.ino)**

### Upload Steps:
1. Open `EchoSense_Unified/EchoSense_Unified.ino` in **Arduino IDE**.
2. Update your Wi-Fi name, password, and laptop IP address at lines 30–36.
3. Plug in your NodeMCU ESP8266.
4. Select **Tools → Board → ESP8266 Boards → NodeMCU 1.0 (ESP-12E Module)**.
5. Select your COM Port under **Tools → Port**.
6. Required Libraries: `NeoPixelBus by Makuna`, `WebSockets by Markus Sattler`, `ArduinoJson`.
7. Click **Upload** (➜).
8. Open the Serial Monitor at **115200** baud. You will see:
   ```text
   ✅ [WiFi] Connected! IP: 192.168.29.yyy
   ✅ [WS] Connected to EchoSense Portal!
   ```
