# EchoSense REST & WebSocket API Specification

## 1. Authentication & Security
- Device-to-Backend endpoints require the `X-Device-Token` HTTP header or `token` query param in WebSocket handshakes matching `ESP32_API_KEY` or `ESP8266_API_KEY`.
- Browser UI connects to `/ws/live` for real-time dashboard telemetry.
- All secrets (WhatsApp tokens, Twilio keys) reside strictly in server environment variables.

---

## 2. REST Endpoints

### 2.1 System & Health

#### `GET /api/status`
Returns complete live status of the system.
**Response (200 OK):**
```json
{
  "system": "EchoSense",
  "version": "1.0.0",
  "uptimeSeconds": 3482,
  "classifier": {
    "status": "RUNNING",
    "model": "YAMNet",
    "sampleRate": 16000
  },
  "microphone": {
    "status": "ACTIVE",
    "source": "ESP32_MIC",
    "lastRms": 0.042
  },
  "devices": {
    "esp32": "ONLINE",
    "esp8266": "ONLINE"
  },
  "notificationService": {
    "provider": "mock",
    "activeContacts": 3
  }
}
```

---

### 2.2 Devices & Heartbeats

#### `GET /api/devices`
Returns status of connected IoT hardware.
**Response (200 OK):**
```json
[
  {
    "deviceId": "ESP32_SENSE_01",
    "type": "ESP32",
    "role": "SENSING_UNIT",
    "ip": "192.168.1.105",
    "rssi": -58,
    "uptimeSeconds": 1240,
    "status": "ONLINE",
    "lastHeartbeat": "2026-09-26T15:10:30Z",
    "secondsSinceHeartbeat": 1.2,
    "firmwareVersion": "1.0.0",
    "sensors": {
      "inmp441": "HEALTHY",
      "sosButton": "READY"
    }
  },
  {
    "deviceId": "ESP8266_ALERT_01",
    "type": "ESP8266",
    "role": "ALERT_UNIT",
    "ip": "192.168.1.106",
    "rssi": -62,
    "uptimeSeconds": 1238,
    "status": "ONLINE",
    "lastHeartbeat": "2026-09-26T15:10:31Z",
    "secondsSinceHeartbeat": 0.8,
    "firmwareVersion": "1.0.0",
    "actuators": {
      "lcd": "ACTIVE",
      "rgbRing": "ACTIVE",
      "buzzer": "READY"
    }
  }
]
```

#### `POST /api/devices/heartbeat`
Telemetry submission sent every 5 seconds by devices.
**Request Body:**
```json
{
  "deviceId": "ESP32_SENSE_01",
  "uptime": 1240,
  "rssi": -58,
  "firmwareVersion": "1.0.0",
  "state": "STREAMING",
  "micHealth": true,
  "buttonState": "IDLE"
}
```

---

### 2.3 Events & Alerts

#### `GET /api/events`
Returns historical sound and emergency events.
**Query Parameters**: `limit=50`, `severity=CRITICAL`

#### `GET /api/events/live`
Returns the instantaneous acoustic evaluation and validation pipeline state.
**Response (200 OK):**
```json
{
  "currentSound": "Possible Alarm",
  "rawLabel": "Alarm",
  "confidence": 0.74,
  "status": "VALIDATING",
  "validation": {
    "confirmations": 2,
    "required": 3,
    "progressPct": 66
  },
  "rmsLevel": 0.082,
  "activeAlert": null
}
```

#### `POST /api/events/sos`
Immediate emergency trigger. Bypasses ML pipeline.
**Request Body:**
```json
{
  "source": "ESP32_PHYSICAL_BUTTON",
  "timestamp": "2026-09-26T15:12:00Z"
}
```

#### `POST /api/events/reset`
Clears active alerts and restores normal listening state.

---

### 2.4 Emergency Contacts Management

#### `GET /api/contacts`
Lists all configured WhatsApp emergency contacts (maximum 5).
**Response (200 OK):**
```json
[
  {
    "id": "c1",
    "name": "Father",
    "phoneNumber": "+12345678901",
    "enabled": true,
    "priority": 1
  }
]
```

#### `POST /api/contacts`
Add new emergency contact. (Rejects if contacts count >= 5).
#### `PUT /api/contacts/{id}`
Update contact information or toggle enabled state.
#### `DELETE /api/contacts/{id}`
Remove contact.
#### `POST /api/contacts/test`
Dispatches a test notification to all active contacts.

---

### 2.5 Development Testing Endpoint

#### `POST /api/test/trigger`
Simulates exact event flows for rapid bench testing.
**Request Body:**
```json
{
  "action": "TEST_CRITICAL",
  "label": "Possible Glass Break",
  "confidence": 0.89
}
```
Available actions:
- `TEST_NORMAL`
- `TEST_WARNING`
- `TEST_CRITICAL`
- `TEST_SOS`
- `TEST_ESP32`
- `TEST_ESP8266`
- `TEST_BUZZER`
- `TEST_LED`
- `TEST_LCD`
- `TEST_WHATSAPP`

---

## 3. WebSocket Endpoints

### 3.1 `/ws/live` (Web Dashboard)
Bidirectional JSON socket. Sends real-time telemetry packets 5-10 times per second:
```json
{
  "type": "LIVE_TELEMETRY",
  "rms": 0.038,
  "label": "Speech",
  "confidence": 0.86,
  "status": "NORMAL",
  "devices": { "esp32": true, "esp8266": true },
  "alert": null
}
```

### 3.2 `/ws/audio` (ESP32 Stream)
Binary WebSocket accepting raw 16-bit 16kHz PCM chunks (typically 1600 - 3200 bytes per frame).

### 3.3 `/ws/esp8266` (ESP8266 Alert Node)
JSON WebSocket dispatching event commands to the ESP8266:
```json
{
  "type": "SET_STATE",
  "priority": 1,
  "severity": "CRITICAL",
  "lcdLine1": "CRITICAL ALERT",
  "lcdLine2": "Alarm Detected",
  "rgbMode": "RED_PULSE",
  "rgbColor": [255, 0, 0],
  "buzzerPattern": "ALARM_BURST",
  "cooldownMs": 25000
}
```
