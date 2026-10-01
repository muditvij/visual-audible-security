"""
ESP32 Hardware Simulation Client.
Emulates an actual ESP32 node connecting over WebSocket, streaming 16-bit PCM chunks,
transmitting heartbeats, and sending physical SOS triggers.
"""

import sys
import time
import json
import asyncio
import numpy as np
import websockets
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

SAMPLE_RATE = 16000
CHUNK_SAMPLES = 800  # 50ms chunk

async def simulate_esp32(backend_url: str = "ws://localhost:8000/ws/audio", duration_seconds: int = 5):
    print(f"\n[ESP32 SIM] Connecting to {backend_url}...")
    try:
        async with websockets.connect(backend_url) as ws:
            print("[ESP32 SIM] Connected successfully! Sending initial heartbeat...")
            
            # 1. Send Heartbeat
            hb = {
                "type": "HEARTBEAT",
                "deviceId": "ESP32_SENSE_01",
                "uptime": 120,
                "rssi": -54,
                "firmwareVersion": "1.0.0",
                "sensors": {"inmp441": "ACTIVE", "sosButton": "READY"}
            }
            await ws.send(json.dumps(hb))
            print("[ESP32 SIM] Heartbeat sent.")

            # 2. Stream simulated audio frames (1kHz test tone)
            print(f"[ESP32 SIM] Streaming audio for {duration_seconds} seconds...")
            start_time = time.time()
            t = 0.0
            dt = 1.0 / SAMPLE_RATE

            while time.time() - start_time < duration_seconds:
                # Generate 50ms chunk of 440Hz tone
                chunk_t = np.linspace(t, t + (CHUNK_SAMPLES * dt), CHUNK_SAMPLES, endpoint=False)
                t += CHUNK_SAMPLES * dt
                audio_floats = 0.3 * np.sin(2 * np.pi * 440 * chunk_t)
                pcm_bytes = (audio_floats * 32767).astype(np.int16).tobytes()
                
                await ws.send(pcm_bytes)
                await asyncio.sleep(0.048)  # ~50ms cadence

            # 3. Simulate Physical SOS Button Press
            print("\n🚨 [ESP32 SIM] Simulating Physical SOS Button Press!")
            sos_pkt = {
                "type": "SOS",
                "deviceId": "ESP32_SENSE_01",
                "timestamp": int(time.time() * 1000),
                "source": "ESP32_PHYSICAL_BUTTON"
            }
            await ws.send(json.dumps(sos_pkt))
            print("[ESP32 SIM] SOS packet dispatched.")
            await asyncio.sleep(1.0)
            
            print("[ESP32 SIM] Simulation completed successfully.")
            return True
    except Exception as e:
        print(f"[ESP32 SIM ERROR] {e}")
        return False

if __name__ == "__main__":
    asyncio.run(simulate_esp32())
