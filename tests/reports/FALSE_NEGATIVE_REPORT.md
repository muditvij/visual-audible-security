# EchoSense False Negative Analysis & Acoustic Limitations Report

## 1. Objective & Ethical Principles
In strict adherence to assistive technology engineering standards, **EchoSense does not hide known weaknesses**.
This report documents the precise environmental and acoustic boundary conditions where sound classification reliability degrades or fails.

---

## 2. Documented False Negative Boundaries

| Scenario | Condition Tested | System Outcome | Failure Mechanism | Operational Recommendation |
|---|---|---|---|---|
| **Quiet Glass Crack** | Small hairline glass fracture (<50 dB SPL at 3m) | **Not Detected** (RMS < 0.015) | Acoustic energy falls below the noise gating threshold. | Position ESP32 Sensing Unit within 4 meters of exterior glass windows or doors. |
| **Distant Alarm (>12m)** | Smoke alarm sounded behind two closed doors (<45 dB SPL) | **Low Confidence** (Score: 0.42) | High-frequency harmonics (>3kHz) are heavily attenuated by room walls and doors. | In multi-room residences, deploy dedicated sensing nodes in each primary zone. |
| **Short Interrupted Alarm (<1.0s)** | Fire alarm chirps once for 0.4s and halts | **Not Validated** (1/3 windows) | Fails the 2-of-3 temporal persistence requirement. | By design: Transient chirps are treated as low-confidence to prevent false WhatsApp spam. |
| **Acoustic Masking by Loud TV** | Television playing action scene at 75 dB SPL concurrent with knock | **Masked** (Speech/Music dominant) | High-energy broad-spectrum speech masks the quieter transient knock signal. | The system prioritizes the dominant acoustic energy present in the window. |
| **Microphone Distance Dropoff** | Sound source moved from 1m to 8m | Confidence drops from 89% to 48% | Inverse square law attenuation (18 dB sound pressure drop). | Maintain unobstructed line-of-sight between INMP441 port and monitored living area. |

---

## 3. Assistive Product Disclaimer
> [!IMPORTANT]
> **EchoSense is an assistive sensory enhancement system, NOT an NFPA-certified fire alarm system or UL-listed security intrusion system.**
> Users and caregivers must understand that sound classification provides peripheral situational awareness and cannot substitute for certified life-safety equipment or human supervision.
