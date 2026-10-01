# EchoSense System Architecture

## 1. Executive Summary

**EchoSense** is a two-device assistive sound awareness and emergency alert system engineered for individuals who have difficulty hearing environmental sounds and/or communicating verbally during emergencies.

The product unifies three logical layers into one coherent, responsive ecosystem:
1. **ESP32 Sensing Unit**: Digital audio acquisition via INMP441 I2S microphone, physical emergency SOS trigger with hardware/software debouncing, and telemetry streaming.
2. **Laptop Intelligence Hub**: High-throughput audio buffer, signal validation (RMS/SNR gating), YAMNet sound classification, multi-window temporal validation engine, event manager with cooldown/priority arbitration, WebSocket broadcast hub, and modular WhatsApp emergency dispatch service.
3. **ESP8266 Alert Unit**: Real-time ambient output node featuring a 16x2 HD44780 parallel LCD (4-bit mode) with differential screen updates, an addressable RGB ring (WS2812) with distinct visual state languages, and a multi-pattern emergency buzzer.

---

## 2. End-to-End System Diagram

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      ESP32 SENSING UNIT (Device 1)                     │
 │                                                                        │
 │  ┌─────────────────┐       ┌────────────────┐      ┌────────────────┐ │
 │  │ INMP441 Digital │ I2S   │ ESP32 DMA      │ PCM  │ WiFi Client    │ │
 │  │ Microphone      │──────>│ Ring Buffer    │─────>│ (WebSocket/TCP)│ │
 │  └─────────────────┘       └────────────────┘      └───────┬────────┘ │
 │                                                            │          │
 │  ┌─────────────────┐ Interrupt     ┌──────────────┐        │          │
 │  │ Physical SOS    │──────────────>│ Debounce &   │────────┘          │
 │  │ Push Button     │               │ Cooldown FSM │ (Priority Event)  │
 │  └─────────────────┘               └──────────────┘                   │
 └────────────────────────────────────────────────────────────┼───────────┘
                                                              │
                                                     Local Network (WiFi)
                                                              │
 ┌────────────────────────────────────────────────────────────▼───────────┐
 │                       LAPTOP INTELLIGENCE HUB                          │
 │                                                                        │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Audio Receiver & Circular Stream Buffer (16 kHz, Mono, PCM)      │  │
 │  └──────────────────────────────────┬───────────────────────────────┘  │
 │                                     ▼                                  │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Preprocessing & Quality Gate: RMS Energy & SNR Silence Filter    │  │
 │  └──────────────────────────────────┬───────────────────────────────┘  │
 │                                     ▼                                  │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ YAMNet Inference Engine: 0.975s Sliding Window (50% Overlap)     │  │
 │  └──────────────────────────────────┬───────────────────────────────┘  │
 │                                     ▼                                  │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Temporal Event Validator: N-of-M Window Persistence Confirmation │  │
 │  └──────────────────────────────────┬───────────────────────────────┘  │
 │                                     ▼                                  │
 │  ┌──────────────────────────────────────────────────────────────────┐  │
 │  │ Event Manager: Cooldown Filter & Centralized Priority Arbiter    │  │
 │  │ (SOS > CRITICAL > WARNING > INFO > NORMAL)                       │  │
 │  └──────┬───────────────────────────┬──────────────────────────┬────┘  │
 │         │                           │                          │       │
 │         ▼                           ▼                          ▼       │
 │  ┌──────────────┐            ┌──────────────┐           ┌────────────┐ │
 │  │ Web Dashboard│            │ WhatsApp Svc │           │ WebSocket  │ │
 │  │ (Live UI)    │            │ (Top 5 Pager)│           │ Hub (LAN)  │ │
 │  └──────────────┘            └──────────────┘           └──────┬─────┘ │
 └────────────────────────────────────────────────────────────────┼───────┘
                                                                  │
                                                         Local Network (WiFi)
                                                                  │
 ┌────────────────────────────────────────────────────────────────▼───────┐
 │                       ESP8266 ALERT UNIT (Device 2)                    │
 │                                                                        │
 │  ┌──────────────────┐        ┌──────────────────┐       ┌───────────┐  │
 │  │ 16x2 HD44780 LCD │        │ Addressable RGB  │       │ Piezo/EM  │  │
 │  │ Parallel 4-Bit   │        │ Ring (WS2812B)   │       │ Buzzer    │  │
 │  │ Differential UI  │        │ Visual State FSM │       │ Patterns  │  │
 │  └────────▲─────────┘        └────────▲─────────┘       └─────▲─────┘  │
 │           │                           │                       │        │
 │           └───────────────────────────┴───────────────────────┘        │
 │                                       │                                │
 │                        ┌──────────────┴─────────────┐                  │
 │                        │ Event Receiver & State FSM │                  │
 │                        │ (Local Fallback & Override)│                  │
 │                        └────────────────────────────┘                  │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Communication Protocols

| Channel | Protocol | Payload Type | Description |
|---|---|---|---|
| ESP32 → Laptop (Audio) | WebSocket Binary / TCP | 16-bit PCM (16 kHz mono) | 1600-sample chunks (100ms frames) |
| ESP32 → Laptop (SOS) | WebSocket JSON / HTTP POST | Application JSON | High-priority SOS payload (`priority: 0`) |
| ESP32 ↔ Laptop (Heartbeat)| WebSocket JSON | Application JSON | Telemetry every 5s (`rssi`, `uptime`, `mic_health`) |
| Laptop → ESP8266 (Events) | WebSocket JSON | Application JSON | Event packet with severity, color, LCD text, buzzer mode |
| ESP8266 ↔ Laptop (Heartbeat)| WebSocket JSON | Application JSON | Telemetry every 5s (`rssi`, `uptime`, `display_state`) |
| Laptop → Frontend | WebSocket JSON | Application JSON | Live audio meters, classifier state, validated alerts |
| Laptop → WhatsApp | HTTPS REST | Graph / Twilio API | Emergency templates dispatched to top 5 contacts |

---

## 4. Priority Arbitration Matrix

State changes and outputs follow a strict strict priority hierarchy. Lower priority events **cannot** overwrite active higher-priority states.

```text
Priority 0 (Highest) : PHYSICAL SOS
Priority 1           : CRITICAL (Glass Break, Smoke Alarm, Fire Alarm, Distress)
Priority 2           : WARNING  (Doorbell, Knock, Siren)
Priority 3           : INFO     (Dog Bark, Clapping)
Priority 4 (Lowest)  : NORMAL   (Speech, Music, Silence/Ambient)
```

### Safety Override Behavior
- When `PHYSICAL SOS` is triggered, it preempts all audio processing output immediately.
- The ESP8266 switches to rapid emergency flashing (Red/Purple strobe), activates the continuous pulsed loud alarm buzzer, and renders `!!! SOS !!! / HELP NEEDED` on the LCD.
- The Laptop backend initiates immediate WhatsApp dispatch to all 5 emergency contacts with verified rate-limit tracking.
- Audio classification continues in the background, but will NOT clear the SOS state until an explicit reset event is commanded.

---

## 5. Temporal Audio Validation Pipeline

Single predictions from neural networks frequently flicker due to ambient acoustic artifacts (e.g. a dropped spoon sounding momentarily like glass breaking). EchoSense avoids false alarms through a 5-stage validation gate:

1. **RMS Energy Pre-check**: If window root-mean-square amplitude is below `AUDIO_RMS_THRESHOLD` (ambient room noise), the window is flagged as SILENCE and bypasses heavy classification.
2. **YAMNet Frame Inference**: Evaluates 15,600 samples (0.975s) producing probabilities across 521 AudioSet classes.
3. **Safety Event Mapping**: Maps raw AudioSet classes to system alerts (e.g., `Glass`, `Shatter` -> `Possible Glass Break`).
4. **N-of-M Window Persistence**: An event is ONLY validated if confirmed in at least **2 out of 3 consecutive windows** with confidence >= `YAMNET_CONFIDENCE_VALID` (0.65).
5. **Cooldown & Hysteresis**: Once an event fires, a 25-second cooldown timer suppresses duplicate notifications while keeping the visual indicator active.

---

## 6. Offline & Fault Tolerance Design

1. **WiFi Disconnection**: Both ESP32 and ESP8266 continuously monitor connection state. If disconnected, automatic exponential backoff reconnects without blocking the main event loops.
2. **Laptop Backend Loss**: If the backend heartbeat ceases for >10 seconds, the ESP8266 LCD reports `BACKEND OFFLINE / System Degraded`.
3. **Local SOS Independence**: If the network is unreachable, pressing the ESP32 SOS button or triggering ESP8266 local inputs will trigger local buzzer and RGB emergency patterns immediately without stalling on network socket timeouts.
