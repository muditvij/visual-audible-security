# EchoSense Hardware & System Troubleshooting Guide

## 1. Electrical Power Budget & Sizing

A frequent point of failure in multi-device IoT systems is inadequate USB power delivery.

| Subsystem | Peak Current | Nominal Current | Supply Rail | Mitigation / Notes |
|---|---|---|---|---|
| **ESP32 Node** | 240 mA (WiFi TX burst) | 80 mA | 5V USB (Onboard 3.3V LDO) | Add 100μF bulk cap on 3.3V rail if brownouts occur. |
| **INMP441 Mic** | 2.5 mA | 1.4 mA | 3.3V ESP32 pin | Very low draw. Connect to clean 3.3V rail. |
| **ESP8266 Node** | 170 mA (WiFi TX burst) | 70 mA | 5V USB (Onboard 3.3V LDO) | Power directly from standard 5V USB adapter. |
| **WS2812 RGB Ring (16 LED)**| **960 mA** (Full White) | **240 mA** (Normal colors) | **NodeMCU VIN (5V Bus)** | **NEVER** power from ESP 3.3V pin! Connect to VIN. |
| **Acoustic Buzzer Module** | 30 mA | 0 mA (Idle) | NodeMCU 3V3 (or VIN) | 3-pin modules draw minimal trigger current from GPIO. |

> [!CAUTION]
> If powering the ESP8266 and the 16-LED ring from an unpowered USB hub, current starvation can trigger ESP8266 watchdog resets (`rst cause:4`).
> Ensure the RGB ring's 5V power wire connects directly to the NodeMCU's **VIN** pin (powered from USB).

---

## 2. ESP8266 Alert Unit Diagnostics

### Symptom: ESP8266 Blue LED Stays Permanently ON / Board Will Not Boot
- **Previous Cause**: GPIO 15 (D8) or GPIO 0 (D3) was pulled to an invalid state at boot.
- **Permanent Solution**:
  - The buzzer is now wired to **D1 (GPIO 5)** and the WS2812 ring is wired to **D2 (GPIO 4)**.
  - GPIO 5 and GPIO 4 are **pure general IO pins** that have zero boot-strapping restrictions.
  - If your board is not booting, verify that no wires are connected to **D8, D3, or D0**.

### Symptom: Buzzer Buzzes Continuously When Idle
- **Cause**: Active-LOW vs Active-HIGH module mismatch.
- **Solution**: In `EchoSense_Unified.ino` (line 339), toggle `#define BUZZER_ACTIVE_LOW true`.

---

## 3. INMP441 Microphone Diagnostics

### Symptom: Audio Stream Received as Constant Zeroes or Silence
- **Cause 1**: The `L/R` channel pin is floating.
  - **Fix**: Connect `L/R` firmly to **GND**. Floating `L/R` causes high-impedance drift and missing I2S data words.
- **Cause 2**: I2S Clock lines swapped.
  - **Fix**: Verify **SCK is on GPIO 14**, **WS is on GPIO 25**, and **SD is on GPIO 32**.
- **Cause 3**: Power supply voltage over limit.
  - **Fix**: Connect VDD to the ESP32 **3V3** pin, NOT 5V (INMP441 maximum absolute rating is 3.6V).

---

## 4. Physical SOS Button Diagnostics

### Symptom: SOS Triggers Continuously or Won't Trigger
- **Cause 1**: Button VCC connected to 5V.
  - **Fix**: Connect button VCC strictly to the ESP32 **3V3** pin.
- **Cause 2**: Polarity misconfiguration.
  - **Fix**: EchoSense includes automatic polarity detection (`BUTTON_AUTO_DETECT true`). On startup, the firmware detects whether your module rests at HIGH or LOW and sets the trigger accordingly. Ensure the button is not held down when powering on the ESP32.

---

## 5. WhatsApp API & Notification Delivery

- **Meta Cloud API Error 190 (Invalid OAuth Access Token)**:
  - Meta Graph API temporary tokens expire after 24 hours. For permanent deployment, configure a System User Token inside Meta Business Manager.
- **Recipient Not Receiving Message**:
  - In Meta Cloud API Sandbox mode, recipient phone numbers must be explicitly whitelisted under "To" numbers in the Meta App Developer Portal.
  - Number format must include international country code without spaces or dashes (e.g. `+14155552671`).
- **Development Fallback**:
  - Set `WHATSAPP_PROVIDER=mock` in `.env` for zero-friction local simulation. All dispatched alerts will log to console, save to SQLite, and display on the Web Dashboard notification tracer.
