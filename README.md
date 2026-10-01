<<<<<<< HEAD
# EchoSense

## Two-Device Assistive Sound Awareness & Emergency Alert System

[![System Architecture](https://img.shields.io/badge/System-Production_Architecture-blue.svg)](#system-architecture)
[![ML Engine](https://img.shields.io/badge/ML-YAMNet_16kHz-success.svg)](#sound-classification--validation)
[![Hardware](https://img.shields.io/badge/Hardware-ESP32_+_ESP8266-orange.svg)](#hardware-wiring--pinouts)
[![Emergency Protocol](https://img.shields.io/badge/Safety-WhatsApp_Top5_+_Physical_SOS-red.svg)](#emergency-sos--whatsapp-integration)

EchoSense is an assistive safety system engineered for individuals who have difficulty hearing environmental sounds and/or communicating verbally during emergencies.

The product integrates **TWO physical IoT devices** and **ONE laptop-based intelligence hub**:
1. **ESP32 Sensing Unit**: Captures 16 kHz digital I2S audio via the INMP441 microphone and handles the physical emergency SOS pushbutton.
2. **Laptop Intelligence Hub**: High-throughput audio ingestion, RMS energy gating, YAMNet classification, N-of-M temporal persistence validation, event manager with cooldown and priority arbitration, real-time Web Dashboard with 60 FPS oscilloscope and 32-band spectrum analyzer, and modular WhatsApp notification delivery.
3. **ESP8266 Alert Unit**: Ambient visual and acoustic feedback featuring an addressable WS2812 RGB LED ring with assistive color states and a multi-pattern acoustic buzzer.

> [!TIP]
> 📖 **Configuring your physical hardware right now?**
> Follow the complete, step-by-step pinout and single-file flashing manual: **[HARDWARE_SETUP_GUIDE.md](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/HARDWARE_SETUP_GUIDE.md)**.
> **Single Unified Firmware**: Use [`EchoSense_Unified/EchoSense_Unified.ino`](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/EchoSense_Unified/EchoSense_Unified.ino) to flash BOTH ESP32 and ESP8266 with no external header linking!

---

## 1. System Architecture

```text
                  ┌──────────────────────────────┐
                  │            LAPTOP            │
                  │                              │
                  │  YAMNet Sound Classification │
                  │  Temporal Event Validation   │
                  │  Event Priority Arbiter      │
                  │  WebSocket Hub & REST API    │
                  │  Web Portal Dashboard        │
                  │  WhatsApp Notification Svc   │
                  └──────────────┬───────────────┘
                                 │
                     WiFi / Local Network (LAN)
                                 │
               ┌─────────────────┴─────────────────┐
               │                                   │
               ▼                                   ▼
       ┌───────────────────┐              ┌────────────────────┐
       │      ESP32        │              │      ESP8266       │
       │   SENSING UNIT    │              │   ALERT UNIT       │
       │                   │              │                    │
       │ INMP441 Mic (I2S) │              │ WS2812 RGB Ring    │
       │ Physical SOS      │              │ Acoustic Buzzer    │
       │ Push Button       │              │ Status LED         │
       └───────────────────┘              └────────────────────┘
=======
# 🛡️ GuardianAI - Standalone Visual & Audible Safety System

**GuardianAI** is a real-time, multimodal emergency detection system that combines computer vision (gesture detection) and audio analysis (acoustic anomaly monitoring) to trigger local emergency responses, record incident logs, and capture camera snapshots.

---

## ✨ Features

- 🖐️ **Visual SOS Gesture Recognition**
  - Powered by **MediaPipe Hand Landmarker**.
  - Detects closed-fist emergency gesture held continuously for **1.8 seconds** to avoid false positives.

- 🔊 **Acoustic Anomaly Detection**
  - Monitors ambient sound continuously via microphone input using `sounddevice` and `numpy`.
  - Tracks a dynamic ambient noise floor to automatically detect audio energy spikes (e.g., screams, shouts, glass shattering).

- 🚨 **Emergency Dispatch & Response**
  - **Audible Alert**: Plays emergency warning beeps asynchronously.
  - **Snapshot Storage**: Automatically saves high-resolution image snapshots of incidents in the `incident_snapshots/` directory.
  - **Event Logging**: Stores event timestamps, event types, and snapshot paths in a local **SQLite** database (`guardian_events.db`).

- 🖥️ **Live HUD Dashboard & Night Guard**
  - Displays real-time system status and an **Audio Level Meter** overlay.
  - Features a **Night Guard** indicator active during restricted hours (10:00 PM – 6:00 AM).

- 🎮 **Camera Fallback & Interactive Simulation**
  - If a webcam is unavailable or locked, the system automatically falls back to an interactive canvas mode with keyboard simulation.

- 📦 **Automatic Model Downloading**
  - Automatically fetches the official Google MediaPipe `hand_landmarker.task` vision model on first run.

---

## 📁 Repository Structure

```text
visual-audible-security/
│
├── sos2.py                    # Main application script
├── requirements.txt           # Python dependencies
├── hand_landmarker.task       # MediaPipe Hand Landmarker model (auto-downloaded)
├── guardian_events.db         # SQLite database logging incidents (auto-generated)
├── incident_snapshots/        # Saved image snapshots during alerts (auto-generated)
└── README.md                  # System documentation
>>>>>>> 0aa90da09b0caf01d15a3246a037bdd4d4e6df7a
```

---

<<<<<<< HEAD
## 2. Directory Structure

```text
EchoSense/
├── esp32/                        # ESP32 Sensing Unit Firmware
│   ├── src/main.cpp              # I2S DMA streaming, SOS interrupt & debounce
│   ├── include/config.h          # WiFi credentials, pinouts, backend host
│   ├── platformio.ini            # PlatformIO build configuration
│   └── README.md                 # Firmware setup and flashing guide
│
├── esp8266/                      # ESP8266 Alert Unit Firmware
│   ├── src/main.cpp              # 16-pin LCD, WS2812 animations, buzzer rhythms
│   ├── include/config.h          # NodeMCU GPIO assignments & contrast config
│   ├── platformio.ini            # PlatformIO build configuration
│   └── README.md                 # Firmware setup and flashing guide
│
├── backend/                      # Laptop Intelligence Hub & Server
│   ├── api/                      # REST routers & WebSocket hub
│   │   ├── routes_status.py      # System health and runtime config
│   │   ├── routes_devices.py     # Real heartbeat telemetry endpoints
│   │   ├── routes_events.py      # Historical events & manual SOS/reset
│   │   ├── routes_contacts.py    # Up to 5 WhatsApp contacts CRUD
│   │   ├── routes_test.py        # Development bench test triggers
│   │   └── websocket_hub.py      # Bidirectional /ws/live, /ws/audio, /ws/esp8266
│   ├── services/                 # Core server logic
│   │   ├── audio_service.py      # Circular stream buffer & inference worker
│   │   ├── device_service.py     # Heartbeat latency & health monitor (No fake online!)
│   │   └── notification_service.py # WhatsApp template dispatcher & rate limiter
│   ├── events/                   # Centralized priority engine
│   │   ├── event_manager.py      # Priority arbiter (SOS > Critical > Warning > Normal)
│   │   └── event_model.py        # Pydantic models for events and contacts
│   ├── notifications/            # Modular WhatsApp providers
│   │   ├── whatsapp_meta.py      # Official Meta Cloud Graph API
│   │   ├── whatsapp_twilio.py    # Twilio Messaging API
│   │   └── whatsapp_mock.py      # Local deterministic testing simulator
│   ├── config/settings.py        # Environment variables and thresholds
│   └── server.py                 # FastAPI application factory & static mount
│
├── ml/                           # YAMNet & Machine Learning Pipeline
│   ├── yamnet/                   # Model classifier & AudioSet taxonomy
│   │   ├── yamnet_classifier.py  # Model loader + Resilient spectral fallback
│   │   ├── yamnet_classes.py     # 521 AudioSet taxonomy labels
│   │   └── yamnet_mapping.py     # Mapping to safety events & priority
│   ├── audio/                    # Signal processing
│   │   ├── preprocessor.py       # 16kHz resampler, DC filter, sliding windows
│   │   ├── rms_analyzer.py       # Linear RMS, dBFS, SNR calculation
│   │   └── buffer_stream.py      # Thread-safe circular audio buffer
│   ├── validation/               # Anti-false alarm engine
│   │   ├── temporal_validator.py # N-of-M persistence gate & cooldown logic
│   │   └── confidence_filter.py  # Low, Valid, High operational tiers
│   └── events/event_classifier.py # Unified pipeline orchestrator
│
├── frontend/                     # Modern Dark-Mode Web Dashboard
│   ├── index.html                # Accessible HTML5 structure
│   ├── app.js                    # Real-time WebSocket DOM binding & state
│   └── styles/                   # Curated CSS design system
│       ├── main.css              # Glassmorphism tokens & typography
│       ├── components.css        # Live sound meters, cards, tables, badges
│       └── animations.css        # Visual alert pulses and breathing effects
│
├── tests/                        # Verification, Benchmarks & Reports
│   ├── audio/                    # Calibrated 16kHz WAV test files
│   ├── hardware/                 # WebSocket hardware simulators (ESP32 & ESP8266)
│   ├── integration/              # Pytest end-to-end and false positive suites
│   └── reports/                  # Engineering reports
│       ├── DAILY_TEST_CHECKLIST.md  # Step-by-step daily test procedure
│       ├── FALSE_POSITIVE_REPORT.md # Clapping vs Glass discrimination
│       └── FALSE_NEGATIVE_REPORT.md # Documented acoustic boundary limits
│
├── docs/                         # In-Depth Engineering Documentation
│   ├── ARCHITECTURE.md           # End-to-end dataflow & resilience models
│   ├── ESP32_CONNECTIONS.md      # Pinout, pull-ups, I2S DMA, debounce circuit
│   ├── ESP8266_CONNECTIONS.md    # 4-bit LCD wiring, WS2812 shifter, buzzer NPN
│   ├── API.md                    # REST schema and WebSocket protocols
│   ├── TESTING.md                # Replay mode and false alarm test matrix
│   └── TROUBLESHOOTING.md        # Electrical budget, LCD contrast, I2S debugging
│
├── run.py                        # Universal CLI entrypoint (Server, Replay, Test)
├── requirements.txt              # Python runtime dependencies
├── .env.example                  # Environment configuration template
└── README.md                     # Product specification and documentation
```

---

## 3. Hardware Wiring & Pinouts

### ESP32 Sensing Unit
Detailed in [docs/ESP32_CONNECTIONS.md](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/docs/ESP32_CONNECTIONS.md):
- **INMP441 VDD**: 3.3V Rail
- **INMP441 GND & L/R**: Common GND
- **INMP441 SCK (BCLK)**: GPIO 14
- **INMP441 WS (LRCK)**: GPIO 25
- **INMP441 SD (DIN)**: GPIO 32
- **Physical 3-Pin SOS Button**: SW1 -> GPIO 18, VCC -> 3.3V (3V3), GND -> GND (Auto-detects Active-LOW / Active-HIGH)

### ESP8266 Alert Unit
Detailed in [docs/ESP8266_CONNECTIONS.md](file:///c:/Users/hp/Desktop/Intellectual%20-%20Copy%20-%20Copy/docs/ESP8266_CONNECTIONS.md):
- **Buzzer Signal (IP/SIG)**: D1 (GPIO 5) — 100% Conflict-free safe IO
- **WS2812 RGB Ring DI**: D2 (GPIO 4) — 100% Conflict-free safe IO
- **Buzzer VCC**: 3V3 (or VIN), GND to GND
- **WS2812 Power**: 5V/VDD to VIN (5V USB bus), GND to GND
- **Status LED**: Built-in Blue LED on D4 (GPIO 2)

---

## 4. Sound Classification & Validation

### Safety Category Mappings
| Audio Event | Safety Category | RGB State | Buzzer Pattern | WhatsApp Alert |
|---|---|---|---|---|
| **Speech** | NORMAL | BLUE | Silent | No |
| **Music** | NORMAL | GREEN | Silent | No |
| **Doorbell** | WARNING | YELLOW pulse | Short periodic beep | No |
| **Knock** | WARNING | YELLOW flash | Short periodic beep | No |
| **Dog Bark** | INFO | ORANGE | Silent | No |
| **Clapping** | INFO | ORANGE | Silent | No |
| **Glass Break** | CRITICAL | RED pulse | Loud alarm burst | **Yes** (Top 5 contacts) |
| **Alarm / Siren** | CRITICAL | RED strobe | Loud alarm burst | **Yes** (Top 5 contacts) |
| **Distress Scream** | CRITICAL | RED pulse | Loud alarm burst | **Yes** (Top 5 contacts) |
| **Physical SOS** | SOS | Emergency strobe | Urgent SOS alarm | **Yes** (Top 5 contacts) |

### Temporal Persistence Gate
Single-window neural network predictions are never trusted blindly for emergency escalation. An event is only validated when:
1. **RMS Energy Gate**: Window energy exceeds room noise baseline (`AUDIO_RMS_THRESHOLD = 0.015`).
2. **Confidence Gate**: Score meets or exceeds `YAMNET_CONFIDENCE_VALID = 0.65`.
3. **Multi-Window Persistence**: Confirmed in at least **2 out of 3 consecutive 0.975-second windows**.
4. **Cooldown Filter**: A 25-second cooldown suppresses redundant alerts.

---

## 5. Quick Start Guide

### Step 1: Install Python Dependencies
=======
## ⚙️ Prerequisites & Setup

### 1. Requirements

- **Python**: Version `3.9` or higher recommended.
- **Hardware**:
  - Webcam / Camera (or run in simulation mode)
  - Microphone for acoustic monitoring
  - Windows OS (for `winsound` emergency buzzer support)

---

### 2. Installation

Clone or download the repository, then install the required dependencies using `pip`:

>>>>>>> 0aa90da09b0caf01d15a3246a037bdd4d4e6df7a
```bash
pip install -r requirements.txt
```

<<<<<<< HEAD
### Step 2: Configure Environment
Copy `.env.example` to `.env` and verify settings:
```bash
cp .env.example .env
```

### Step 3: Run Audio Replay Mode
Execute bit-exact verification on a sample glass break or alarm benchmark:
```bash
python run.py --replay tests/audio/sample_glass_break.wav
```

### Step 4: Run Automated Test Suite
```bash
python run.py --test
```

### Step 5: Start Production Hub & Web Dashboard

#### Option A: Running with Laptop Built-in Microphone (Zero Hardware Mode)
If you haven't wired your ESP32 yet and want to test live voice, phone alarms, or claps immediately through your computer's mic:
```bash
python run.py --server --mic
```

#### Option B: Running with Remote ESP32 I2S Microphone
```bash
python run.py --server --port 8000
```
Open **`http://localhost:8000`** in your browser.
*(You can also toggle the Laptop Microphone on/off anytime from the web dashboard using the top-right **🎤 Enable Laptop Mic** button).*

---

## 6. Assistive Disclaimer
EchoSense is an assistive sensory enhancement system designed to provide peripheral situational awareness and an immediate physical emergency SOS mechanism. It is **not** an NFPA-certified fire protection system or UL-listed security device. Always verify situations before taking action.
=======
---

## 🚀 Running the System

Start the safety monitor by executing:

```bash
python sos2.py
```

### Controls & Simulation Keys

| Key / Gesture | Action |
|---|---|
| **Hold Fist (1.8s)** | Triggers Visual SOS Distress alert & snapshot |
| **Loud Sound / Scream** | Triggers Acoustic Threat Alert & snapshot |
| **`s`** (Canvas Mode) | Simulates Visual SOS Gesture |
| **`a`** (Canvas Mode) | Simulates Acoustic Threat |
| **`q`** | Safely exits the application |

---

## 🗄️ Incident Logging & Database

When an emergency event is triggered, an entry is written to `guardian_events.db` in the `event_logs` table:

```sql
CREATE TABLE event_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT,
    event_type TEXT,
    snapshot_path TEXT
);
```

Snapshots are stored as:
`incident_snapshots/INCIDENT_YYYYMMDD_HHMMSS.jpg`

---

## 🔧 System Configuration

You can customize detection sensitivity and timing directly inside [sos2.py](file:///c:/Users/win%2010/Desktop/My-project/SOS_Detector/visual-audible-security/sos2.py):

```python
# Audio Spike Sensitivity Multiplier
AUDIO_SPIKE_FACTOR = 3.5

# Restricted Night Guard Hours (24h format)
RESTRICTED_START_HOUR = 22  # 10 PM
RESTRICTED_END_HOUR = 6     # 6 AM

# Required SOS Fist Gesture Hold Time (seconds)
REQUIRED_SOS_HOLD_TIME = 1.8
```

---

## 📜 License

This project is open-source and intended for safety research and educational implementation.
>>>>>>> 0aa90da09b0caf01d15a3246a037bdd4d4e6df7a
