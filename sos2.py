import cv2
import mediapipe as mp
import time
import os
import urllib.request
import numpy as np
import threading
import sounddevice as sd
import sqlite3
import winsound  # Built-in Windows emergency buzzer sound
from datetime import datetime

# ==========================================
# ⚙️ SYSTEM CONFIGURATION
# ==========================================
# Audio Detection Config
AUDIO_SPIKE_FACTOR = 3.5  # Trigger when volume exceeds 3.5x average room noise
SAMPLE_RATE = 44100
NOISE_FLOOR_MEMORY = 50   # Moving average window for ambient noise

# Restricted Night Hours (24-hour format: 22 = 10 PM, 6 = 6 AM)
RESTRICTED_START_HOUR = 22
RESTRICTED_END_HOUR = 6

# Vision Hold Timers
REQUIRED_SOS_HOLD_TIME = 1.8  # Seconds to hold fist gesture

# MediaPipe Hand Landmark IDs
FINGERTIPS = [8, 12, 16, 20]
FINGER_PIPS = [6, 10, 14, 18]

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"

# System States
audio_energy = 0.0
ambient_noise_floor = 0.02
audio_threat_flag = False
alarm_cooldown = False

# Create Snapshots directory
os.makedirs("incident_snapshots", exist_ok=True)

# ==========================================
# 🗄️ LOCAL DATABASE INITIALIZATION
# ==========================================
def init_db():
    conn = sqlite3.connect("guardian_events.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            event_type TEXT,
            snapshot_path TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

def log_incident_to_db(event_type, snapshot_path):
    """Saves incident record to local SQLite database."""
    conn = sqlite3.connect("guardian_events.db")
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO event_logs (timestamp, event_type, snapshot_path) VALUES (?, ?, ?)",
        (timestamp, event_type, snapshot_path)
    )
    conn.commit()
    conn.close()

# ==========================================
# 📦 MODEL INITIALIZATION
# ==========================================
if not os.path.exists(MODEL_PATH):
    print("[INFO] Downloading precision vision model...")
    urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    print("[INFO] Download completed successfully!")

BaseOptions = mp.tasks.BaseOptions
HandLandmarker = mp.tasks.vision.HandLandmarker
HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
RunningMode = mp.tasks.vision.RunningMode

options = HandLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=MODEL_PATH),
    running_mode=RunningMode.IMAGE,
    num_hands=2,
    min_hand_detection_confidence=0.75,
    min_hand_presence_confidence=0.75,
    min_tracking_confidence=0.75
)

landmarker = HandLandmarker.create_from_options(options)

# ==========================================
# 🔊 LOCAL EMERGENCY RESPONSE
# ==========================================
def trigger_local_alert(frame, event_type):
    """Saves snapshot, logs to DB, and sounds emergency buzzer."""
    global alarm_cooldown
    if alarm_cooldown:
        return
        
    alarm_cooldown = True
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    snapshot_filename = f"incident_snapshots/INCIDENT_{timestamp_str}.jpg"
    
    # Save Snapshot
    cv2.imwrite(snapshot_filename, frame)
    
    # Save to SQL Database
    log_incident_to_db(event_type, snapshot_filename)
    
    print(f"\n[🚨 EMERGENCY DISPATCHED] Type: {event_type}")
    print(f"[LOGGED TO DB] Snapshot saved -> {snapshot_filename}\n")

    # Sound alarm asynchronously
    def play_buzzer():
        try:
            for _ in range(3):
                winsound.Beep(2500, 300) # High frequency alert beep
                time.sleep(0.1)
        except Exception:
            pass

    threading.Thread(target=play_buzzer, daemon=True).start()
    threading.Timer(5.0, reset_cooldown).start()

def reset_cooldown():
    global alarm_cooldown
    alarm_cooldown = False

# ==========================================
# 🎤 ACOUSTIC ANOMALY MONITORING
# ==========================================
def audio_monitor_thread():
    """Monitors live sound and compares against dynamic background noise floor."""
    global audio_energy, ambient_noise_floor, audio_threat_flag

    recent_rms = []

    def audio_callback(indata, frames, time_info, status):
        global audio_energy, ambient_noise_floor, audio_threat_flag
        
        # Calculate Root Mean Square energy
        rms = np.sqrt(np.mean(indata**2))
        audio_energy = min(1.0, rms * 12)
        
        # Dynamic noise floor tracking
        recent_rms.append(rms)
        if len(recent_rms) > NOISE_FLOOR_MEMORY:
            recent_rms.pop(0)
            
        ambient_noise_floor = np.mean(recent_rms) + 0.01
        
        # Detection check: Sound spike higher than noise floor multiplier
        if rms > (ambient_noise_floor * AUDIO_SPIKE_FACTOR) and rms > 0.15:
            audio_threat_flag = True

    try:
        with sd.InputStream(callback=audio_callback, channels=1, samplerate=SAMPLE_RATE, blocksize=2048):
            while True:
                sd.sleep(100)
    except Exception as e:
        print(f"[WARN] Microphone offline: {e}")

# ==========================================
# 👁️ VISION HELPER FUNCTIONS
# ==========================================
def is_sos_fist(hand_landmarks):
    """Accurately verifies if all four fingers are folded down into an emergency fist."""
    curled = 0
    for tip, pip in zip(FINGERTIPS, FINGER_PIPS):
        if hand_landmarks[tip].y > hand_landmarks[pip].y:
            curled += 1
    return curled == 4

def is_restricted_hours():
    """Checks if current time falls into restricted night hours."""
    current_hour = datetime.now().hour
    if RESTRICTED_START_HOUR > RESTRICTED_END_HOUR:
        return current_hour >= RESTRICTED_START_HOUR or current_hour < RESTRICTED_END_HOUR
    else:
        return RESTRICTED_START_HOUR <= current_hour < RESTRICTED_END_HOUR

def render_hud(frame, system_status="MONITORING"):
    """Renders dashboard UI overlay."""
    h, w, _ = frame.shape
    
    # Header Overlay
    cv2.rectangle(frame, (0, 0), (w, 55), (20, 20, 20), -1)
    
    # Status Indicator Light
    status_color = (0, 255, 0) if "MONITORING" in system_status else (0, 0, 255)
    cv2.circle(frame, (25, 27), 8, status_color, -1)
    cv2.putText(frame, f"GUARDIAN-AI | STATUS: {system_status}", (45, 33),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    # Audio Level Meter (Bottom Left)
    meter_w = 140
    fill_w = int(audio_energy * meter_w)
    cv2.rectangle(frame, (20, h - 35), (20 + meter_w, h - 20), (50, 50, 50), -1)
    cv2.rectangle(frame, (20, h - 35), (20 + fill_w, h - 20), (0, 255, 255), -1)
    cv2.putText(frame, "AUDIO LEVEL", (20, h - 42), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

    # Restricted Hours Badge (Bottom Right)
    if is_restricted_hours():
        cv2.putText(frame, "[NIGHT GUARD ACTIVE]", (w - 200, h - 25), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

def initialize_camera():
    for b_code in [cv2.CAP_ANY, cv2.CAP_DSHOW, cv2.CAP_MSMF]:
        for idx in [0, 1, 2]:
            cap = cv2.VideoCapture(idx, b_code)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    return cap
                cap.release()
    return None

# ==========================================
# 🚀 MAIN LOOP
# ==========================================
# Start background audio listener
t_audio = threading.Thread(target=audio_monitor_thread, daemon=True)
t_audio.start()

cap = initialize_camera()
use_demo = cap is None

if use_demo:
    print("[INFO] Camera stream locked/unavailable. Running interactive simulation canvas.")

sos_hold_start = None

print("\n" + "="*50)
print("  GUARDIAN-AI : STANDALONE SAFETY SYSTEM")
print("="*50)
print("• Vision Threat : Hold tight fist for 1.8s")
print("• Audio Threat  : Clap or shout near mic")
print("• Logs Database : guardian_events.db")
print("• Snapshots Dir : /incident_snapshots/")
print("• Exit System   : Press 'q' key in window")
print("="*50 + "\n")

while True:
    if not use_demo:
        ret, frame = cap.read()
        if not ret or frame is None:
            use_demo = True
            continue
        frame = cv2.flip(frame, 1)
    else:
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(frame, "Interactive Simulation (Press 's': Fist | 'a': Scream)", 
                    (20, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

    h, w, _ = frame.shape
    gesture_detected = False

    # Process Vision Stream
    if not use_demo:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        results = landmarker.detect(mp_image)

        if results.hand_landmarks:
            for hand_landmarks in results.hand_landmarks:
                mp.tasks.vision.drawing_utils.draw_landmarks(
                    frame, hand_landmarks, mp.tasks.vision.HandLandmarksConnections.HAND_CONNECTIONS
                )
                if is_sos_fist(hand_landmarks):
                    gesture_detected = True

    # Check key commands
    key = cv2.waitKey(20) & 0xFF
    if key == ord('q'):
        break
    if use_demo:
        if key == ord('s'): gesture_detected = True
        if key == ord('a'): audio_threat_flag = True

    current_status = "MONITORING"

    # Threat Priority Pipeline
    # 1. Acoustic Threat Trigger
    if audio_threat_flag:
        current_status = "ACOUSTIC ANOMALY DETECTED"
        cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 8)
        cv2.putText(frame, "!!! ACOUSTIC THREAT DETECTED !!!", (50, h // 2), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        trigger_local_alert(frame, event_type="Acoustic Threat (Scream/Glass Shatter)")
        audio_threat_flag = False

    # 2. Visual SOS Gesture Trigger
    elif gesture_detected:
        if sos_hold_start is None:
            sos_hold_start = time.time()

        elapsed = time.time() - sos_hold_start
        progress = min(1.0, elapsed / REQUIRED_SOS_HOLD_TIME)

        bar_w = int(progress * (w - 100))
        cv2.rectangle(frame, (50, 70), (50 + bar_w, 85), (0, 165, 255), -1)
        cv2.putText(frame, f"HOLD FOR SOS: {int(progress * 100)}%", (50, 65),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 2)

        if elapsed >= REQUIRED_SOS_HOLD_TIME:
            current_status = "EMERGENCY SOS ACTIVE"
            cv2.rectangle(frame, (0, 0), (w, h), (0, 0, 255), 10)
            cv2.putText(frame, "!!! EMERGENCY SOS DISTRESS !!!", (50, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)
            
            trigger_local_alert(frame, event_type="Visual Distress SOS Gesture")
    else:
        sos_hold_start = None

    # Draw HUD Overlay
    render_hud(frame, system_status=current_status)
    cv2.imshow("GuardianAI - Local Safety System", frame)

if cap:
    cap.release()
cv2.destroyAllWindows()
landmarker.close()