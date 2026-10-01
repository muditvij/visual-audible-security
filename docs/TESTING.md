# EchoSense Verification & Testing Guide

## 1. Testing Methodology

EchoSense implements a 4-tier verification protocol to guarantee reliable detection without false alarm fatigue:
1. **Unit Verification**: Algorithmic tests for RMS calculation, confidence filters, and temporal state machines.
2. **Replay Mode**: Bit-exact WAV playback through the live inference and validation pipeline.
3. **False Positive & Negative Stress Testing**: High-noise environmental benchmarking.
4. **Hardware & Failure Mode Emulation**: WiFi dropouts, power interruptions, and socket disconnects.

---

## 2. Replay Mode Execution

Replay mode allows running standard audio benchmarks through the exact validation stack as live hardware:

```bash
# Replay a glass break sample
python run.py --replay tests/audio/sample_glass_break.wav

# Replay an alarm sample
python run.py --replay tests/audio/sample_alarm.wav

# Replay normal conversational speech
python run.py --replay tests/audio/sample_speech.wav
```

### Expected Replay Output
```text
[REPLAY] Loading audio file: tests/audio/sample_glass_break.wav
[REPLAY] Format: 16000Hz, Mono, 16-bit PCM (Duration: 3.2s)
[REPLAY] Window 1 [0.0s - 1.0s]: Raw=Glass (0.78), RMS=0.062 -> Candidate: Possible Glass Break [1/3]
[REPLAY] Window 2 [0.5s - 1.5s]: Raw=Glass (0.86), RMS=0.081 -> Candidate: Possible Glass Break [2/3] -> VALIDATED!
[EVENT] Dispatching CRITICAL event: Possible Glass Break (Confidence: 86%)
[ESP8266] State updated: LCD="WARNING / Glass Break", RGB=RED, Buzzer=ALARM_BURST
[NOTIFY] WhatsApp dispatch triggered to 5 emergency contacts.
```

---

## 3. False Positive Testing Matrix

To protect users against alert fatigue, safety alerts are subjected to false-positive discrimination tests:

| Input Sound Source | Raw Acoustic Similarity | Target Filter Behavior | Validation Rule |
|---|---|---|---|
| **Loud Clapping** | High transient spike (like glass) | Suppressed | Clapping lacks high-frequency resonance of shattering glass; temporal filter requires multi-window persistence. |
| **Door Slam / Cabinet** | Low-frequency thump | Classified as KNOCK or NORMAL | RMS threshold filters low-frequency boom without high-frequency energy. |
| **Phone Ringtone / Jingle** | Tonal bursts (like alarm) | Suppressed or INFO | Standard ringtones do not match continuous smoke/fire alarm duty cycles (temporal window fails N=3). |
| **Loud TV / Movie Speech** | High vocal energy | Classified as SPEECH | Mapped to NORMAL (Blue LED, no alarm). |
| **High Fan / AC Noise** | Steady broadband hiss | Filtered by RMS SNR gate | Background noise baseline subtracted; bypasses YAMNet. |

---

## 4. False Negative Testing Matrix

Documenting system limits is critical for safety-assistive technology:

| Scenario | Acoustic Condition | System Behavior & Mitigation |
|---|---|---|
| **Distant Alarm (>15m)** | Low SNR (<6dB above ambient) | Flagged as LOW-CONFIDENCE. Amber LED pulse, no emergency WhatsApp. |
| **Quiet Glass Crack** | Low amplitude, single window | Requires proximity to INMP441 (<5 meters for unamplified micro-breaks). |
| **Muffled Distress** | Acoustic occlusion behind closed door | User is instructed to position ESP32 centrally in primary living spaces. |

---

## 5. Daily Real-World Operational Checklist

1. **Hardware Boot Verification**:
   - Power ESP32 -> Verify blue LED steady (WiFi connected).
   - Power ESP8266 -> Verify LCD displays `ECHOSENSE / System Ready`, RGB glows GREEN.
2. **Normal Audio Check**:
   - Speak near ESP32 -> Web UI reflects `Speech` (Normal), RGB shows BLUE, Buzzer silent.
3. **Warning Audio Check**:
   - Ring doorbell or rap sharply on table -> LCD displays `DOORBELL` / `KNOCK`, RGB shows YELLOW.
4. **Physical SOS Check**:
   - Press ESP32 SOS button -> Immediate RED/PURPLE fast flash, loud alarm buzzer, Web UI shows `SOS ACTIVE`.
   - Click `Reset Alert` on dashboard to return to listening state.
5. **Network Resilience Check**:
   - Disconnect WiFi router or laptop server for 15 seconds.
   - Verify ESP8266 LCD reports `BACKEND OFFLINE`.
   - Re-enable WiFi -> Verify automatic re-connection within 10 seconds.
