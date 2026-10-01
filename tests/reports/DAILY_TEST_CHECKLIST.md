# EchoSense Daily Operational Testing Checklist

This checklist must be performed on the physical hardware setup or bench test harness before operating EchoSense.

---

## 1. Hardware Power-On & Boot Verification

| Item | Test Action | Expected Result | Pass/Fail |
|---|---|---|---|
| 1.1 | Power on ESP32 Sensing Unit | Blue LED flashes during WiFi handshake, then turns solid ON. Serial monitor prints `Connected! IP: 192.168.x.x`. | [ ] |
| 1.2 | Power on ESP8266 Alert Unit | LCD displays `ECHOSENSE / Starting...`, then `ECHOSENSE / System Ready`. RGB Ring transitions from blue to GREEN. | [ ] |
| 1.3 | Start Laptop Intelligence Hub (`python run.py --server`) | Web dashboard accessible at `http://localhost:8000`. ESP32 and ESP8266 indicator dots turn GREEN within 5s. | [ ] |

---

## 2. Normal Acoustic Scenarios (No False Alarms)

| Item | Sound Source | Expected System Behavior | Pass/Fail |
|---|---|---|---|
| 2.1 | Ambient Room Silence (AC / Fan humming) | RMS Energy < 0.015. LCD: `LISTENING... / Monitoring`. RGB: BLUE. Buzzer: Silent. No notification. | [ ] |
| 2.2 | Conversational Human Speech | Classified as `Speech`. Confidence: >70%. LCD: `LISTENING... / Speech`. RGB: BLUE. Buzzer: Silent. | [ ] |
| 2.3 | Background Instrumental Music | Classified as `Music`. LCD: `LISTENING... / Music`. RGB: GREEN. Buzzer: Silent. | [ ] |
| 2.4 | Clapping / Applause | Classified as `Clapping`. LCD: `SOUND DETECTED / Clapping`. RGB: ORANGE. Buzzer: Silent. | [ ] |

---

## 3. Warning Sound Scenarios

| Item | Sound Source | Expected System Behavior | Pass/Fail |
|---|---|---|---|
| 3.1 | Front Doorbell Chime / Ding-dong | Classified as `Doorbell`. LCD: `SOUND DETECTED / Doorbell`. RGB: YELLOW pulse. Buzzer: Short periodic beep. | [ ] |
| 3.2 | Sharp Knocks on Door / Table | Classified as `Knock`. LCD: `SOUND DETECTED / Knock`. RGB: YELLOW flash. Buzzer: Short periodic beep. | [ ] |

---

## 4. Critical Safety Alert Scenarios

| Item | Sound Source | Expected System Behavior | Pass/Fail |
|---|---|---|---|
| 4.1 | Shattering Glass or Replay `sample_glass_break.wav` | Temporal validator confirms 2/3 windows. LCD: `WARNING / Glass Break`. RGB: RED pulse. Buzzer: Loud continuous burst. WhatsApp: Sent to 5 emergency contacts. | [ ] |
| 4.2 | Smoke / Fire Alarm or Replay `sample_alarm.wav` | Temporal validator confirms continuous tone. LCD: `CRITICAL ALERT / Alarm Detected`. RGB: RED strobe. Buzzer: Loud alarm. WhatsApp: Sent to 5 contacts. | [ ] |
| 4.3 | Cooldown & Anti-Spam Check | Play alarm continuously for 20 seconds. Confirm only **1 WhatsApp batch** is dispatched (cooldown active). | [ ] |

---

## 5. Physical Emergency SOS Mechanism

| Item | Test Action | Expected System Behavior | Pass/Fail |
|---|---|---|---|
| 5.1 | Press ESP32 Physical SOS Push Button | **IMMEDIATE OVERRIDE**: Bypasses YAMNet. LCD: `!!! SOS !!! / HELP NEEDED`. RGB: Red/Purple/White fast strobe. Buzzer: Urgent SOS alternating tones. WhatsApp dispatched to all 5 contacts. | [ ] |
| 5.2 | Rapid Repeated Pressing | Press SOS button 5 times within 2 seconds. Verify debouncing and cooldown ensures only **1 emergency event** is registered. | [ ] |
| 5.3 | Dashboard Reset Action | Click `Reset Alert State` on web dashboard. System returns immediately to `ECHOSENSE / System Ready`, RGB returns to GREEN, Buzzer silences. | [ ] |

---

## 6. Network Dropout & Resilience Checks

| Item | Test Action | Expected System Behavior | Pass/Fail |
|---|---|---|---|
| 6.1 | Disconnect WiFi Router / Turn off Laptop Hub | ESP8266 LCD reports `BACKEND OFFLINE / System Degraded` within 10 seconds. RGB pulses ORANGE. | [ ] |
| 6.2 | Restore WiFi / Laptop Hub | Both ESP32 and ESP8266 auto-reconnect without requiring hardware reboot within 15 seconds. | [ ] |
| 6.3 | Local Emergency Independence | With network disconnected, press SOS button. Local buzzer and strobe must fire instantly. | [ ] |
