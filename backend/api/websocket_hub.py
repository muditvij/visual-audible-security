"""
EchoSense Real-Time WebSocket Hub.
Manages bidirectional connections with Web Dashboard clients, ESP8266 alert unit,
and high-throughput binary audio streaming from the ESP32 sensing node.
"""

import json
import logging
from typing import Set, Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

from backend.config.settings import settings
from backend.services.audio_service import audio_service
from backend.services.device_service import device_service
from backend.events.event_manager import event_manager
from backend.events.event_model import EchoSenseEvent

logger = logging.getLogger("EchoSense.WebSocketHub")

class WebSocketHub:
    def __init__(self):
        # Connected web browsers
        self.active_ui_sockets: Set[WebSocket] = set()
        # Connected ESP8266 devices
        self.esp8266_sockets: Set[WebSocket] = set()
        # Connected ESP32 devices
        self.esp32_sockets: Set[WebSocket] = set()
        # Stored main thread asyncio event loop
        self.main_loop: Optional[Any] = None
        
        # Wire up event manager state changes to automatically push to all nodes
        event_manager.register_state_listener(self.broadcast_event_state)
        # Wire up audio service live telemetry to web dashboard
        audio_service.subscribe_telemetry(self.broadcast_live_telemetry)

    def set_event_loop(self, loop):
        self.main_loop = loop
        logger.info("[WS Hub] Registered main event loop for background thread broadcasts.")

    def _get_loop(self):
        if self.main_loop and self.main_loop.is_running():
            return self.main_loop
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            if loop and loop.is_running():
                self.main_loop = loop
                return loop
        except RuntimeError:
            pass
        return None

    # --- UI Clients ---
    async def connect_ui(self, websocket: WebSocket):
        import asyncio
        if not self.main_loop or not self.main_loop.is_running():
            try:
                self.main_loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
        await websocket.accept()
        self.active_ui_sockets.add(websocket)
        logger.info(f"Dashboard UI client connected (Active: {len(self.active_ui_sockets)})")
        
        # Send initial full state
        await self.send_full_ui_sync(websocket)

    def disconnect_ui(self, websocket: WebSocket):
        self.active_ui_sockets.discard(websocket)
        logger.info(f"Dashboard UI client disconnected (Remaining: {len(self.active_ui_sockets)})")

    async def send_full_ui_sync(self, websocket: WebSocket):
        """Push initial state snapshot upon dashboard load."""
        devices = device_service.get_all_devices()
        history = [e.model_dump() for e in event_manager.get_history(limit=20)]
        active_alert = event_manager.active_event.model_dump() if event_manager.active_event else None
        
        payload = {
            "type": "INITIAL_SYNC",
            "devices": devices,
            "activeAlert": active_alert,
            "latestTelemetry": audio_service.latest_telemetry,
            "recentEvents": history
        }
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            logger.error(f"Error sending UI sync: {e}")

    # --- ESP8266 Alert Device ---
    async def connect_esp8266(self, websocket: WebSocket):
        await websocket.accept()
        self.esp8266_sockets.add(websocket)
        client_ip = websocket.client.host if websocket.client else "127.0.0.1"
        device_service.set_device_status("ESP8266_ALERT_01", "ONLINE", client_ip=client_ip)
        logger.info(f"ESP8266 Alert Device connected via WebSocket from {client_ip}.")
        
        # Broadcast updated device status to all UI dashboards immediately
        self.broadcast_device_update()

        # Sync current state to ESP8266 immediately
        current_event = event_manager.active_event or EchoSenseEvent(
            eventId="init",
            displayLabel="System Ready",
            rgbColor=[255, 255, 255],
            rgbMode="WHITE_BREATH",
            buzzerPattern="OFF"
        )
        await self.send_to_esp8266(current_event)

    def disconnect_esp8266(self, websocket: WebSocket):
        self.esp8266_sockets.discard(websocket)
        device_service.record_disconnect("ESP8266_ALERT_01")
        logger.warning("ESP8266 Alert Device disconnected.")
        self.broadcast_device_update()

    # --- ESP32 Sensing Device ---
    async def connect_esp32(self, websocket: WebSocket):
        await websocket.accept()
        self.esp32_sockets.add(websocket)
        client_ip = websocket.client.host if websocket.client else "127.0.0.1"
        device_service.set_device_status("ESP32_SENSE_01", "ONLINE", client_ip=client_ip)
        logger.info(f"ESP32 Sensing Unit connected via WebSocket from {client_ip}.")
        self.broadcast_device_update()

    def disconnect_esp32(self, websocket: WebSocket):
        self.esp32_sockets.discard(websocket)
        device_service.record_disconnect("ESP32_SENSE_01")
        logger.warning("ESP32 Sensing Unit disconnected.")
        self.broadcast_device_update()

    async def send_to_esp8266(self, event: EchoSenseEvent):
        """Send command packet to ESP8266 with explicit acknowledge signaling."""
        is_ack = (event.source == "MANUAL_RESET" or event.priority == 4 or "Ready" in event.displayLabel or "Reset" in event.rawLabel)
        payload = {
            "type": "SET_STATE",
            "eventId": event.eventId,
            "priority": event.priority,
            "severity": event.severity,
            "displayLabel": event.displayLabel,
            "rgbColor": event.rgbColor,
            "rgbMode": event.rgbMode,
            "buzzerPattern": event.buzzerPattern,
            "cooldownSeconds": int(settings.EVENT_COOLDOWN_SECONDS),
            "isAcknowledge": is_ack
        }
        msg = json.dumps(payload)
        for sock in list(self.esp8266_sockets):
            try:
                await sock.send_text(msg)
                if is_ack:
                    await sock.send_text(json.dumps({"type": "ACKNOWLEDGE"}))
            except Exception as e:
                logger.error(f"Error dispatching to ESP8266 socket: {e}")

    def broadcast_device_update(self):
        """Push latest device states to UI clients."""
        import asyncio
        loop = self._get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_broadcast_devices(), loop)

    async def _async_broadcast_devices(self):
        if not self.active_ui_sockets:
            return
        payload = {
            "type": "DEVICE_UPDATE",
            "devices": device_service.get_all_devices()
        }
        msg = json.dumps(payload)
        for sock in list(self.active_ui_sockets):
            try:
                await sock.send_text(msg)
            except Exception:
                pass

    # --- Broadcast Dispatchers ---
    def broadcast_event_state(self, event: EchoSenseEvent):
        """Called synchronously by EventManager when state changes."""
        import asyncio
        loop = self._get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_broadcast_event(event), loop)
        else:
            logger.debug("[WS Hub] Cannot broadcast event state: No running event loop.")

    async def _async_broadcast_event(self, event: EchoSenseEvent):
        # 1. Update ESP8266
        await self.send_to_esp8266(event)
        
        # 2. Update UI dashboards
        payload = {
            "type": "STATE_CHANGE",
            "event": event.model_dump(),
            "devices": device_service.get_all_devices()
        }
        msg = json.dumps(payload)
        dead_sockets = []
        for sock in list(self.active_ui_sockets):
            try:
                await sock.send_text(msg)
            except Exception:
                dead_sockets.append(sock)
        for s in dead_sockets:
            self.active_ui_sockets.discard(s)

    def broadcast_live_telemetry(self, telemetry: Dict[str, Any]):
        """Called at high frequency by AudioService background worker."""
        if not self.active_ui_sockets:
            return
        import asyncio
        loop = self._get_loop()
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(self._async_broadcast_telemetry(telemetry), loop)

    async def _async_broadcast_telemetry(self, telemetry: Dict[str, Any]):
        if not self.active_ui_sockets:
            return
        payload = {
            "type": "LIVE_TELEMETRY",
            "telemetry": telemetry,
            "devices": device_service.get_all_devices()
        }
        msg = json.dumps(payload)
        dead_sockets = []
        for sock in list(self.active_ui_sockets):
            try:
                await sock.send_text(msg)
            except Exception:
                dead_sockets.append(sock)
        for s in dead_sockets:
            self.active_ui_sockets.discard(s)

ws_hub = WebSocketHub()
