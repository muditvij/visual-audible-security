"""
ESP8266 Hardware Simulation Client.
Emulates an actual ESP8266 Alert node: connects to backend WebSocket,
receives SET_STATE commands, simulates LCD/RGB/Buzzer actuators, and sends heartbeats.
"""

import sys
import time
import json
import asyncio
import websockets

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

async def simulate_esp8266(backend_url: str = "ws://localhost:8000/ws/esp8266", listen_seconds: int = 6):
    print(f"\n[ESP8266 SIM] Connecting to {backend_url}...")
    try:
        async with websockets.connect(backend_url) as ws:
            print("[ESP8266 SIM] Connected to EchoSense Hub!")
            
            # Send initial heartbeat
            hb = {
                "type": "HEARTBEAT",
                "deviceId": "ESP8266_ALERT_01",
                "uptime": 60,
                "rssi": -58,
                "firmwareVersion": "1.1.0",
                "actuators": {"rgbRing": "ACTIVE", "buzzer": "READY"}
            }
            await ws.send(json.dumps(hb))
            print("[ESP8266 SIM] Heartbeat sent.")

            print(f"[ESP8266 SIM] Listening for state commands ({listen_seconds}s)...")
            start = time.time()
            while time.time() - start < listen_seconds:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=1.5)
                    data = json.loads(msg)
                    if data.get("type") == "SET_STATE":
                        print(f"\n💡 [ESP8266 ALERT ACTUATORS UPDATED]")
                        print(f"   Event:     {data.get('displayLabel', '')}")
                        print(f"   RGB Mode:  {data.get('rgbMode', '')} (Color: {data.get('rgbColor', [])})")
                        print(f"   Buzzer:    {data.get('buzzerPattern', 'OFF')}")
                        print(f"   Priority:  {data.get('priority', 4)}")
                except asyncio.TimeoutError:
                    pass

            print("\n[ESP8266 SIM] Simulation finished successfully.")
            return True
    except Exception as e:
        print(f"[ESP8266 SIM ERROR] {e}")
        return False

if __name__ == "__main__":
    asyncio.run(simulate_esp8266())
