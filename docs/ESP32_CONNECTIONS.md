# ESP32 Sensing Unit Hardware & Wiring Specification

## 1. Module Overview
The ESP32 Sensing Unit is responsible for acquiring continuous environmental audio via the INMP441 I2S digital microphone, monitoring the physical emergency SOS button, streaming audio frames to the laptop, and transmitting telemetry.

---

## 2. GPIO Pin Assignment Table

| Component | Component Pin | ESP32 GPIO | Mode | Boot Strapping Considerations |
|---|---|---|---|---|
| **INMP441** | VDD | 3.3V (Pin 3V3) | Power | Operates on 1.8V - 3.3V. Connect to clean 3.3V rail. |
| **INMP441** | GND | GND | Power | Common ground with ESP32. |
| **INMP441** | L/R | GND | Config | Tied to GND to configure microphone on Left I2S channel. |
| **INMP441** | SD (Serial Data) | **GPIO 32** | I2S DIN (Input) | Safe input pin. No boot-strapping conflicts. |
| **INMP441** | WS (Word Select) | **GPIO 25** | I2S WS / LRCK (Output) | Clean DAC/GPIO. Avoids strapping pin conflicts. |
| **INMP441** | SCK (Serial Clock) | **GPIO 14** | I2S SCK / BCLK (Output) | Safe general IO. |
| **SOS Button (3-Pin)** | SW1 (Signal) | **GPIO 18** | Input | Switch signal line (Auto-detects Active-LOW / Active-HIGH). |
| **SOS Button (3-Pin)** | VCC | **3.3V (3V3)** | Power | Power for onboard resistor. **CRITICAL: Connect to 3.3V, NOT 5V!** |
| **SOS Button (3-Pin)** | GND | **GND** | Ground | Common system ground. |
| **Status LED** | Onboard LED | **GPIO 2** | Output | Built-in Blue LED indicates connection/streaming status. |

---

## 3. INMP441 Digital Microphone Connection Details

The INMP441 is an omnidirectional MEMS digital microphone with an integrated 24-bit I2S ADC. 

### Wiring Diagram
```text
  INMP441 Breakout                  ESP32 DevKit (30/38 pin)
  ┌──────────────┐                  ┌───────────────────────┐
  │         VDD  │─────────────────>│ 3V3 (3.3V Rail)        │
  │         GND  │─────────────────>│ GND                    │
  │         L/R  │─────────────────>│ GND (Selects Left Ch) │
  │          WS  │─────────────────>│ GPIO 25 (LRCK)         │
  │         SCK  │─────────────────>│ GPIO 14 (BCLK)         │
  │          SD  │─────────────────>│ GPIO 32 (DIN)          │
  └──────────────┘                  └───────────────────────┘
```

> [!IMPORTANT]
> The INMP441 is a **digital I2S sensor**, not an analog electret capsule. Never connect the SD line to ADC analog pins or attempt `analogRead()`.
> Grounding `L/R` assigns the microphone samples to the left channel in the 32-bit I2S frame.

---

## 4. 3-Pin Physical SOS Button Module Wiring & Architecture (GND, VCC, SW1)

### Module Pinout & Connections
The physical SOS button is a 3-pin module with an onboard pull-up or pull-down resistor:

| Module Pin | ESP32 Pin | Purpose | Critical Note |
|---|---|---|---|
| **VCC** (or `+`) | **3.3V (3V3)** | Module power reference | **NEVER connect to 5V/VIN**! Must use 3.3V to protect GPIO 18. |
| **GND** (or `-`) | **GND** | Ground reference | Connect to any ESP32 GND pin. |
| **SW1** (or `S` / `OUT`) | **GPIO 18** | Digital switch signal output | Monitored by hardware interrupt on ESP32. |

### Circuit Topology
```text
   3.3V Rail (ESP32 3V3) ────────┐
                                 │
                               ┌─┴────────────────────────┐
                               │ 3-Pin SOS Button Module  │
                               │                          │
                               │ VCC   (Pin 1)            │
   GND Rail  (ESP32 GND) ──────┤ GND   (Pin 2)            │
                               │ SW1   (Pin 3)            │
                               └─┬────────────────────────┘
                                 │
   ESP32 GPIO 18 ────────────────┘
```

### Auto-Detection & Debounce Architecture
1. **Dynamic Polarity Detection**: On startup, the ESP32 samples the idle line voltage on GPIO 18. If the module is Active-LOW (idle HIGH), it configures a `FALLING` interrupt. If the module is Active-HIGH (idle LOW), it configures a `RISING` interrupt.
2. **Software Debounce**: 50ms stable active state required before validating trigger.
3. **Emergency Lock & Cooldown**: Upon detection, the ESP32 enters a latching SOS state for 5 seconds to prevent spamming while guaranteeing rapid delivery.
4. **Autonomous Transmit**: The SOS packet is sent over a dedicated socket with immediate retry.

---

## 5. Boot Pin Analysis & Safety Verification

To prevent ESP32 boot failures or flash bricking, the following pins were analyzed:
- **GPIO 0**: Reserved for flash boot mode. Kept free.
- **GPIO 2**: Onboard LED. High impedance or standard output. Safe.
- **GPIO 12 (MTDI)**: Controls flash voltage (3.3V vs 1.8V). Pulling high can damage flash. **NOT USED**.
- **GPIO 15**: Outputs boot ROM debug log. **NOT USED for I2S clocks** to avoid bus noise during reset.
- **GPIO 34, 35, 36, 39**: Input-only pins without internal pull-ups. Reserved for analog inputs if needed.

All assigned pins (14, 18, 25, 32) are fully verified and safe for boot.
