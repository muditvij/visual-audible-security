# ESP8266 Alert Unit Hardware & Wiring Specification

## 1. Module Overview
The ESP8266 Alert Unit serves as the primary physical output device for EchoSense, providing immediate sensory feedback via:
1. **Addressable WS2812 RGB LED Ring** (NeoPixel): Peripheral visual sound awareness and emergency visual strobe.
2. **Acoustic Buzzer Module**: Distinct sound patterns for normal, warning, critical alarm, and urgent SOS states.
3. **Onboard Telemetry & Offline Safety**: Status LED for Wi-Fi/WebSocket connection state and automatic fallback if the network hub is offline.

> [!NOTE]
> **Removal of 16-Pin HD44780 LCD Display**:
> The 16-pin parallel LCD display has been eliminated. The web portal dashboard now serves as the primary visual display for detailed metrics, live oscilloscope waveforms, frequency spectrums, and historical event tables, while the physical Alert Unit remains ultra-compact, reliable, and wire-free with only 2 control signal lines.

---

## 2. GPIO Pin Assignment Table & Boot Safety Analysis

The ESP8266 microcontroller has strict hardware boot-strapping requirements on several pins:
- **GPIO 0 (D3)**: Must be HIGH for normal flash boot. (Pulling LOW forces UART download mode).
- **GPIO 2 (D4)**: Must be HIGH for normal flash boot. (Connected to internal pull-up and onboard LED).
- **GPIO 15 (D8)**: Must be LOW for normal flash boot. (Any pull-up or external resistance pulling HIGH halts boot).

### Selected Safe Standard Pinout
To eliminate boot hangs, freeze states, and flash errors, EchoSense uses exclusively **non-strapping, general-purpose pins**:

| Component | Component Pin | NodeMCU Pin | ESP8266 GPIO | Boot Behavior | Engineering Role |
|---|---|---|---|---|---|
| **Buzzer Module** | **IP / SIG / S** | **D1** | **GPIO 5** | Pure General IO | Safe at boot. No strapping restrictions. Drives acoustic buzzer. |
| **WS2812 RGB Ring** | **DI (Data In)** | **D2** | **GPIO 4** | Pure General IO | Safe at boot. No strapping restrictions. NeoPixelBus DMA/UART output. |
| **Status LED** | Onboard LED | **D4** | **GPIO 2** | Built-in Blue LED | High at boot. Blinks on reconnect, solid ON when linked. |
| **Buzzer VCC** | VCC / + | **3V3** *(or VIN)* | Power Rail | 3.3V power (or 5V from USB VIN). |
| **RGB Ring Power** | 5V / VDD | **VIN** | 5V Rail | 5V direct from USB. **Never use 3.3V pin for RGB ring!** |
| **Common Ground** | GND / - | **GND** | Ground Rail | Common reference between ESP8266, buzzer, and ring. |

---

## 3. Wiring Diagram

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
                            │ 3V3                D8 │ (Kept Free - No Boot Hangs!)
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

---

## 4. Addressable RGB Ring (WS2812B) Details

### Power Supply Rules:
> [!WARNING]
> An addressable 16-LED NeoPixel ring at full white brightness draws up to **960 mA**.
> The ESP8266 onboard 3.3V low-dropout voltage regulator is only rated for ~300 mA. Powering the ring from the 3.3V pin will cause voltage sag, triggering continuous brownout resets (`rst cause:4`).
> **Always connect the ring's 5V/VDD pin to the `VIN` (or `VU`) pin on the NodeMCU**, which draws clean 5V directly from the USB port.

### Signal Integrity:
- Connect the **DI (Data In)** line of the WS2812 ring directly to **NodeMCU D2 (GPIO 4)**.
- For long wire runs (>15 cm), an optional 330Ω series resistor between D2 and DI reduces ringing reflections.

---

## 5. Acoustic Buzzer Wiring

### Standard 3-Pin Buzzer Module (Recommended):
Modern 3-pin buzzer modules include an onboard transistor driver, base resistor, and flyback diode.
- Connect **IP (or SIG / S)** to **NodeMCU D1 (GPIO 5)**.
- Connect **VCC (or +)** to **NodeMCU 3V3** (or VIN).
- Connect **GND (or -)** to **NodeMCU GND**.

### Active-HIGH vs Active-LOW Logic:
- EchoSense defaults to **Active-HIGH** (sound plays when GPIO 5 is driven HIGH).
- If your buzzer sounds continuously when idle, toggle `BUZZER_ACTIVE_LOW true` in the firmware.

---

## 6. Single-File Firmware Upload

The firmware for this unit is compiled directly from the single unified sketch:
- **`EchoSense_Unified/EchoSense_Unified.ino`**
- In Arduino IDE, select board: **NodeMCU 1.0 (ESP-12E Module)** and click **Upload**.
- The compiler automatically links the Alert Unit logic with zero external configuration files.
