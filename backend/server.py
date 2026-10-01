"""
EchoSense Main Backend Server & Application Factory.
Provides REST APIs, WebSocket channels, static frontend hosting, and background ML lifecycle.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.config.settings import settings
from backend.services.audio_service import audio_service
from backend.services.notification_service import notification_service
from backend.services.device_service import device_service
from backend.events.event_manager import event_manager
from backend.api.websocket_hub import ws_hub

from backend.api.routes_status import router as status_router
from backend.api.routes_devices import router as devices_router
from backend.api.routes_events import router as events_router
from backend.api.routes_contacts import router as contacts_router
from backend.api.routes_test import router as test_router
from backend.api.routes_audio import router as audio_router

# Setup structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("EchoSense.Server")

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup:
    logger.info("=================================================================")
    logger.info("            ECHOSENSE SYSTEM STARTUP INITIALIZATION             ")
    logger.info("=================================================================")
    
    # 1. Register main asyncio event loop with ws_hub for thread-safe cross-thread broadcasts
    import asyncio
    ws_hub.set_event_loop(asyncio.get_running_loop())
    
    # 2. Wire event notifications
    event_manager.register_notification_listener(notification_service.dispatch_alert)
    
    # 3. Start real-time audio analysis engine
    audio_service.start()
    
    # 3. Check if Laptop Microphone was requested
    if os.getenv("USE_LAPTOP_MIC", "False").lower() in ("true", "1"):
        logger.info("🎤 Auto-activating Host Laptop Microphone on startup...")
        audio_service.start_laptop_mic()
    
    logger.info("EchoSense Backend running. Ready for ESP devices and Web Portal.")
    yield
    # Shutdown:
    logger.info("Stopping EchoSense background tasks...")
    audio_service.stop()
    logger.info("EchoSense Backend successfully halted.")

app = FastAPI(
    title="EchoSense Intelligence Hub",
    description="Assistive Sound Awareness & Emergency Alert Hub for ESP32 and ESP8266 IoT Units",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware for LAN access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register REST Routers
app.include_router(status_router)
app.include_router(devices_router)
app.include_router(events_router)
app.include_router(contacts_router)
app.include_router(test_router)
app.include_router(audio_router)

# Mount Static Assets for Frontend Dashboard
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_file = FRONTEND_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"status": "EchoSense API Operational", "dashboard": "Frontend loading..."})

# --- WebSocket Channels ---

@app.websocket("/ws/live")
async def websocket_live_dashboard(websocket: WebSocket):
    """Real-time live telemetry channel for Web Dashboard."""
    await ws_hub.connect_ui(websocket)
    try:
        while True:
            # Keepalive receiver
            data = await websocket.receive_text()
            # Handle client ping
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_hub.disconnect_ui(websocket)
    except Exception as e:
        logger.error(f"Error in UI websocket: {e}")
        ws_hub.disconnect_ui(websocket)

@app.websocket("/ws/esp8266")
async def websocket_esp8266(websocket: WebSocket, token: Optional[str] = None):
    """Dedicated bidirectional socket for ESP8266 Alert Unit."""
    await ws_hub.connect_esp8266(websocket)
    try:
        while True:
            # ESP8266 sends heartbeat / sensor states
            msg_text = await websocket.receive_text()
            try:
                import json
                payload = json.loads(msg_text)
                if payload.get("type") == "HEARTBEAT":
                    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
                    device_service.record_heartbeat(payload, client_ip=client_ip)
            except Exception as pe:
                logger.debug(f"Non-JSON or parse error from ESP8266: {pe}")
    except WebSocketDisconnect:
        ws_hub.disconnect_esp8266(websocket)
    except Exception as e:
        logger.error(f"Error in ESP8266 websocket: {e}")
        ws_hub.disconnect_esp8266(websocket)

@app.websocket("/ws/audio")
async def websocket_esp32_audio(websocket: WebSocket, token: Optional[str] = None):
    """High-throughput binary PCM stream endpoint for ESP32 Sensing Unit."""
    await ws_hub.connect_esp32(websocket)
    logger.info("ESP32 Audio Stream connected via binary WebSocket.")
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    
    # Record initial device connection
    device_service.record_heartbeat({
        "deviceId": "ESP32_SENSE_01",
        "type": "ESP32",
        "uptime": 1,
        "rssi": -55,
        "firmwareVersion": "1.0.0",
        "sensors": {"inmp441": "STREAMING", "sosButton": "READY"}
    }, client_ip=client_ip)
    
    try:
        while True:
            message = await websocket.receive()
            if "bytes" in message and message["bytes"]:
                # Ingest raw 16-bit PCM bytes
                audio_service.ingest_pcm_chunk(message["bytes"], sample_width=settings.AUDIO_SAMPLE_WIDTH)
            elif "text" in message and message["text"]:
                # Handle text control messages (e.g. SOS or heartbeat from ESP32)
                import json
                try:
                    payload = json.loads(message["text"])
                    if payload.get("type") == "SOS":
                        event_manager.trigger_sos(source="ESP32_PHYSICAL_BUTTON")
                    elif payload.get("type") == "HEARTBEAT":
                        device_service.record_heartbeat(payload, client_ip=client_ip)
                        ws_hub.broadcast_device_update()
                except Exception as pe:
                    logger.debug(f"ESP32 control parse error: {pe}")
    except WebSocketDisconnect:
        ws_hub.disconnect_esp32(websocket)
        logger.info("ESP32 Audio Stream disconnected.")
    except Exception as e:
        ws_hub.disconnect_esp32(websocket)
        if "disconnect message has been received" in str(e):
            logger.info("ESP32 client closed connection.")
        else:
            logger.error(f"Error in ESP32 audio websocket: {e}")
