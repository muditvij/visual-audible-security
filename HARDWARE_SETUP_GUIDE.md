# EchoSense: Complete Hardware Setup & Flashing Manual

This guide provides the complete, step-by-step instructions to wire, configure, and flash both the **ESP32 Sensing Unit** and the **ESP8266 Alert Unit** using **clean, standalone, separate single-file code** with **zero external header dependencies or complex linking**.

---

## ⚡ Quick Reference Pinout Summary

### 1. ESP8266 Alert Unit (WS2812 RGB Ring & Acoustic Buzzer)
> [!NOTE]
> **16-Pin Parallel LCD Removed!**
> The old 16-pin LCD display has been **completely eliminated**. All live waveforms, 32-band spectrum graphs, and historical incident logs are visualized on the **Web Dashboard Portal** (`http://localhost:8000`), while the physical Alert Unit uses only **2 signal wires** for maximum reliability and zero boot hangs.

| Component | Component Pin | NodeMCU Pin | GPIO | Recommended Wire Color | Engineering Notes |
|---|---|---|---|---|---|
| **Acoustic Buzzer** | **IP / SIG / S** | **D1** | **GPIO 5** | Yellow | **100% Conflict-Free**: Non-strapping pin. Never causes boot lockups! |
| **Acoustic Buzzer** | **VCC / +** | **3V3** *(or VIN)* | 3.3V Rail | Red | Safe power rail (works reliably at 3.3V - 5V). |
| **Acoustic Buzzer** | **GND / -** | **GND** | Ground Rail | Black | System ground. |
| **WS2812 RGB Ring** | **DI (Data In)** | **D2** | **GPIO 4** | Green | **100% Conflict-Free**: Direct Adafruit NeoPixel bit-bang pin. |
| **WS2812 RGB Ring** | **5V / VDD** | **VIN** | 5V USB Bus | Red | **Must use VIN (5V USB rail)!** NEVER power from 3.3V pin! |
| **WS2812 RGB Ring** | **GND** | **GND** | Ground Rail | Black | System ground. |
| **Status LED** | Onboard LED | **D4** | **GPIO 2** | Built-in | Blinks when connecting, Solid Blue when synced with portal. |

---

### 2. ESP32 Sensing Unit (INMP441 Microphone & Physical SOS)
| Component | Component Pin | ESP32 DevKit Pin | Recommended Wire Color | Purpose & Critical Safety Rules |
|---|---|---|---|---|
| **INMP441 Mic** | **VDD** | **3.3V (3V3)** | Red | Clean 3.3V power. Do **NOT** connect to 5V! |
| **INMP441 Mic** | **GND** | **GND** | Black | System ground reference. |
| **INMP441 Mic** | **L/R** | **GND** | Black / Gray | Ties microphone to **Left Channel** in I2S frame. (Never leave floating!) |
| **INMP441 Mic** | **SCK** | **GPIO 14** | Yellow | Serial Bit Clock (BCLK) master clock. |
| **INMP441 Mic** | **WS** | **GPIO 25** | Green | Word Select (LRCK) sample window framing. |
| **INMP441 Mic** | **SD** | **GPIO 32** | Blue | Serial Data IN (DIN) 24-bit PCM stream. |
| **SOS Button (3-Pin)**| **VCC** (or `+`) | **3.3V (3V3)** | Red | **CRITICAL: Connect to 3.3V, NEVER 5V!** Overvoltage burns GPIO 18! |
| **SOS Button (3-Pin)**| **GND** (or `-`) | **GND** | Black | Ground reference rail. |
| **SOS Button (3-Pin)**| **SW1** (or `S`) | **GPIO 18** | White / Orange | Digital switch signal output (Hardware interrupt). |
| **Status LED** | Onboard LED | **GPIO 2** | Built-in | Blinks when connecting, Solid Blue when streaming audio. |

---

## 🌟 PART 1: The Standalone Firmware Files

You have **two options** for flashing:
- **Option A (Recommended - Separate Files)**:
  - ESP8266 Alert Unit: **[`esp8266/esp8266.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/esp8266/esp8266.ino)** (or in sketchbook: [`arduino/esp8266/esp8266.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/arduino/esp8266/esp8266.ino))
  - ESP32 Sensing Unit: **[`esp32/esp32.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/esp32/esp32.ino)** (or in sketchbook: [`arduino/esp32/esp32.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/arduino/esp32/esp32.ino))
- **Option B (Unified Single File)**:
  - Both Units in One File: **[`EchoSense_Unified/EchoSense_Unified.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/EchoSense_Unified/EchoSense_Unified.ino)**

> [!TIP]
> **Zero External Linking**: Each `.ino` file is 100% standalone! There are no `#include "config.h"` dependencies, no missing header errors, and all configurations are right at the top of the file.

---

## PART 2: Arduino IDE Setup & Library Installation

### Step 1: Install Board Packages (One-Time Setup)
1. Open **Arduino IDE**.
2. Go to **File → Preferences**.
3. In **Additional Boards Manager URLs**, paste:
   ```text
   https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json,
   http://arduino.esp8266.com/stable/package_esp8266com_index.json
   ```
4. Go to **Tools → Board → Boards Manager**, search and install:
   - **esp32** (by Espressif Systems)
   - **esp8266** (by ESP8266 Community)

### Step 2: Install Required Libraries (One-Time Setup)
Go to **Sketch → Include Library → Manage Libraries** and search/install:
1. **Adafruit NeoPixel** (by Adafruit) — *Essential for the WS2812 RGB LED ring on ESP8266!*
2. **WebSockets** (by Markus Sattler / links2004) — *For low-latency real-time telemetry.*
3. **ArduinoJson** (by Benoit Blanchon, v7.x or v6.x) — *For high-speed message parsing.*

---

## PART 3: ESP8266 Alert Unit Wiring Diagram

```text
                                NODEMCU ESP8266
                            ┌───────────────────────┐
                            │ A0 (ADC0)          D0 │
                            │ RSV                D1 ├──> Buzzer Signal (GPIO 5)
                            │ RSV                D2 ├──> WS2812 Data In (GPIO 4)
                            │ SD3                D3 │
                            │ SD2                D4 ├──> Status LED (GPIO 2)
                            │ SD1               3V3 ├──> Buzzer VCC (3.3V)
                            │ CMD               GND ├──> Common Ground
                            │ SD0                D5 │
                            │ CLK                D6 │
                            │ GND                D7 │
                            │ 3V3                D8 │ (Kept Free - Zero Boot Hangs!)
                            │ EN                 RX │
                            │ RST                TX │
                            │ GND               GND │
                            │ VIN (+5V Rail)    3V3 │
                            └─┬─────────────────────┘
                              │
          ┌───────────────────┘
          │ (5V from USB)
          ▼
   ┌──────────────┐                  ┌────────────────────────┐
   │ WS2812 RING  │                  │  3-PIN BUZZER MODULE   │
   │              │                  │                        │
   │ 5V / VDD     │                  │ VCC: 3V3 (or VIN)      │
   │ GND: GND     │                  │ GND: GND               │
   │ DI:  D2 (G4) │                  │ IP:  D1 (GPIO 5)       │
   └──────────────┘                  └────────────────────────┘
```

### Why D1 and D2 are the Ultimate Safe Pins:
- On ESP8266, **D8 (GPIO 15)** must be LOW at boot, and **D3 (GPIO 0)** / **D4 (GPIO 2)** affect bootloader mode. Previous designs using D8 or D4 caused boot hangs and frozen LEDs!
- **D1 (GPIO 5)** and **D2 (GPIO 4)** are completely free general-purpose I/O pins. They have **zero boot restrictions**, guaranteeing that your board boots up 100% of the time!

---

## PART 4: ESP32 Sensing Unit Wiring Diagram

```text
               ESP32 DEVKIT (30 or 38 Pin)
         ┌───────────────────────────────────┐
         │ 3V3 ───┬────────────────────── GND ├──────┐
         │ EN     │                      GPIO23      │
         │ VP     │                      GPIO22      │
         │ VN     │                      TX0         │
         │ GPIO34 │                      RX0         │
         │ GPIO35 │                      GPIO21      │
         │ GPIO32 ┼──────────────┐       GPIO19      │
         │ GPIO33 │              │       GPIO18 ◄─┐  │
         │ GPIO25 ┼────────┐     │       GPIO5    │  │
         │ GPIO26 │        │     │       GPIO17   │  │
         │ GPIO27 │        │     │       GPIO16   │  │
         │ GPIO14 ┼──┐     │     │       GPIO4    │  │
         │ GPIO12 │  │     │     │       GPIO0    │  │
         │ GND    │  │     │     │       GPIO2    │  │ (Status LED)
         │ VIN    │  │     │     │       GPIO15   │  │
         └────────┼──┼─────┼─────┼────────────────┼──┘
                  │  │     │     │                │
                  │  │     │     │                ▼
                  │  │     │     │          ┌───────────┐
                  │  │     │     │          │ 3-PIN SOS │
                  │  │     │     │          │  BUTTON   │
                  │  │     │     │          │  MODULE   │
                  │  │     │     │          └──┬───┬────┘
                  │  │     │     │             │   │
                  │  │     │     │             │   └── VCC (3.3V)
                  │  │     │     │             └────── GND
                  ▼  ▼     ▼     ▼
             ┌─────────────────────────┐
             │       INMP441           │
             │   I2S DIGITAL MIC       │
             │                         │
             │ VDD: 3V3     L/R: GND   │
             │ GND: GND     SCK: 14    │
             │ WS:  25      SD:  32    │
             └─────────────────────────┘
```

---

## PART 5: Step-by-Step Code Flashing Guide

### Step 1: Flash the ESP8266 Alert Unit
1. Connect your **NodeMCU ESP8266** board to your laptop using a Micro-USB data cable.
2. In Arduino IDE, open:
   `esp8266/esp8266.ino`
3. Verify your Wi-Fi name, password, and laptop IP address at lines 30–34:
   ```cpp
   #define WIFI_SSID           "VijHouse-JioFiber-4G"
   #define WIFI_PASSWORD       "mudit@9152787816"
   #define BACKEND_HOST        "192.168.29.19"
   #define BACKEND_PORT        8000
   ```
4. In **Tools → Board → ESP8266 Boards**, select **NodeMCU 1.0 (ESP-12E Module)**.
5. In **Tools → Port**, select your ESP8266 COM port.
6. Click **Upload (➜)**.
7. **Watch the board immediately upon completion**:
   - **Buzzer**: Chirps twice to verify audio hardware.
   - **LED Ring**: Lights up immediately in bright **Cyan-Blue**, then changes to a **Rotating Yellow Chase** while connecting to Wi-Fi.
   - **When Connected**: Turns solid vibrant **Green** and plays a double connection chime!

---

### Step 2: Flash the ESP32 Sensing Unit
1. Disconnect the ESP8266 and plug in your **ESP32** board.
2. In Arduino IDE, open:
   `esp32/esp32.ino`
3. Verify the same Wi-Fi name, password, and laptop IP address at lines 26–30.
4. In **Tools → Board → esp32**, select **ESP32 Dev Module** (or your specific ESP32 board).
5. In **Tools → Port**, select your ESP32 COM port.
6. Click **Upload (➜)**.
   *(Tip: If the IDE console displays `Connecting........_____.....`, press and hold the **BOOT** button on the ESP32 board for 2 seconds until the writing percentage begins).*
7. Open the **Serial Monitor** at `115200` baud:
   ```text
   [I2S] INMP441 Microphone ready at 16000 Hz.
   ✅ [WiFi] Connected! IP Address: 192.168.29.xxx
   ✅ [WS] Connected to EchoSense Hub at 192.168.29.19:8000
   ```

---

## PART 6: Live Verification with Web Portal

1. **Start the Laptop Backend Server**:
   Open a terminal in the project directory and run:
   ```powershell
   python run.py --server --port 8000
   ```
2. **Open the Web Portal**:
   Navigate to **`http://localhost:8000`** in your browser.
   - **ESP32 Sensing Unit Card**: Shows **ONLINE** (green dot) with live RSSI meter.
   - **ESP8266 Alert Unit Card**: Shows **ONLINE** (green dot) with live RSSI meter.
   - **Live Audio Visualizer**: 60 FPS oscilloscope waveform and 32-band spectrum visualizer animate with room acoustics.
3. **Test Sound Detection**:
   - Speak, knock on the table, clap, or play an alarm tone on your phone near the ESP32.
   - The portal classifies the sound and immediately updates the WS2812 RGB ring and buzzer!
4. **Test Physical Emergency SOS**:
   - Press the physical push button on the ESP32.
   - **Instant Synchronized Response**:
     - **LED Ring**: Flashes ultra-fast **Emergency Strobe** (Red / Magenta / Pure White).
     - **Buzzer**: Emits continuous urgent SOS alarm rhythm.
     - **Web Portal**: Displays persistent red alert banner: `PHYSICAL SOS EMERGENCY ACTIVATED`.
     - **WhatsApp**: Dispatches emergency alert to top 5 contacts.
5. **Reset**:
   - Click **Reset Alert State** on the web dashboard to return the system to normal ambient monitoring.

---

## PART 7: Troubleshooting Checklist

| Issue | Root Cause | Instant Fix |
|---|---|---|
| **Ring LED not glowing** | Previously using NeoPixelBus UART method on D4 instead of D2. | Use the updated `esp8266.ino` with **Adafruit NeoPixel** and ensure Data In is on **D2 (GPIO 4)**. |
| **Ring LED power reset** | Ring 5V pin connected to ESP8266 3.3V pin. | Move the Ring 5V wire to **NodeMCU VIN** (5V direct from USB). |
| **Buzzer not making sound** | Passive buzzer received DC without frequency oscillation. | Use the updated `esp8266.ino` which uses `tone(BUZZER_PIN, freq)`. It beeps on boot immediately. |
| **Buzzer sounds continuously** | Buzzer module is Active-LOW. | Change `#define BUZZER_ACTIVE_LOW true` in `esp8266.ino`. |
| **Device not connecting to portal** | Laptop IP changed on Wi-Fi network. | Run `ipconfig` in PowerShell, note your IPv4 Address, and update `BACKEND_HOST` in the sketch. |
| **Microphone reads silence** | INMP441 `L/R` pin floating. | Firmly connect the **L/R** pin to **GND** on the ESP32. |
