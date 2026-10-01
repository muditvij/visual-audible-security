"""
EchoSense IoT Device Management & Real Heartbeat Monitor.
Guarantees NO FAKE DATA: Device statuses transition dynamically between
ONLINE, DEGRADED, and OFFLINE strictly based on real network heartbeats.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from backend.config.settings import settings

logger = logging.getLogger("EchoSense.DeviceService")

class DeviceService:
    def __init__(self):
        self.devices: Dict[str, Dict[str, Any]] = {
            "ESP32_SENSE_01": {
                "deviceId": "ESP32_SENSE_01",
                "type": "ESP32",
                "role": "SENSING_UNIT",
                "ip": "0.0.0.0",
                "rssi": 0,
                "uptimeSeconds": 0,
                "status": "OFFLINE",
                "lastHeartbeat": 0.0,
                "firmwareVersion": "1.0.0",
                "sensors": {
                    "inmp441": "UNKNOWN",
                    "sosButton": "UNKNOWN"
                }
            },
            "ESP8266_ALERT_01": {
                "deviceId": "ESP8266_ALERT_01",
                "type": "ESP8266",
                "role": "ALERT_UNIT",
                "ip": "0.0.0.0",
                "rssi": 0,
                "uptimeSeconds": 0,
                "status": "OFFLINE",
                "lastHeartbeat": 0.0,
                "firmwareVersion": "1.0.0",
                "actuators": {
                    "rgbRing": "UNKNOWN",
                    "buzzer": "UNKNOWN"
                }
            }
        }

    def set_device_status(self, device_id: str, status: str, client_ip: Optional[str] = None):
        """Immediately update status (e.g. on socket connect or disconnect)."""
        if device_id in self.devices:
            self.devices[device_id]["status"] = status
            if status == "ONLINE":
                self.devices[device_id]["lastHeartbeat"] = time.time()
                if client_ip:
                    self.devices[device_id]["ip"] = client_ip
            logger.info(f"[DeviceService] Device {device_id} status set to {status}")

    def record_disconnect(self, device_id: str):
        """Mark device as OFFLINE on socket closure."""
        if device_id in self.devices:
            self.devices[device_id]["status"] = "OFFLINE"
            logger.info(f"[DeviceService] Device {device_id} disconnected -> OFFLINE")

    def record_heartbeat(self, payload: Dict[str, Any], client_ip: str = "127.0.0.1") -> Dict[str, Any]:
        """Update device telemetry from real heartbeat packet."""
        device_id = payload.get("deviceId", "UNKNOWN_DEV")
        now = time.time()
        
        # If device not yet registered, register it dynamically
        if device_id not in self.devices:
            dev_type = "ESP32" if "32" in device_id else "ESP8266"
            self.devices[device_id] = {
                "deviceId": device_id,
                "type": dev_type,
                "role": "SENSING_UNIT" if dev_type == "ESP32" else "ALERT_UNIT",
                "ip": client_ip,
                "rssi": payload.get("rssi", -60),
                "uptimeSeconds": payload.get("uptime", 0),
                "status": "ONLINE",
                "lastHeartbeat": now,
                "firmwareVersion": payload.get("firmwareVersion", "1.0.0"),
                "sensors": {},
                "actuators": {}
            }
        
        dev = self.devices[device_id]
        dev["lastHeartbeat"] = now
        dev["ip"] = client_ip
        dev["rssi"] = payload.get("rssi", dev["rssi"])
        dev["uptimeSeconds"] = payload.get("uptime", dev["uptimeSeconds"])
        dev["firmwareVersion"] = payload.get("firmwareVersion", dev["firmwareVersion"])
        dev["status"] = "ONLINE"
        
        if "sensors" in payload:
            dev["sensors"].update(payload["sensors"])
        if "actuators" in payload:
            dev["actuators"].update(payload["actuators"])
            
        logger.debug(f"Heartbeat received from {device_id} (RSSI: {dev['rssi']} dBm)")
        return dev

    def get_all_devices(self) -> List[Dict[str, Any]]:
        """Return all device states with dynamic online/offline computation."""
        now = time.time()
        results = []
        for dev_id, dev in self.devices.items():
            dev_copy = dict(dev)
            last_hb = dev.get("lastHeartbeat", 0.0)
            
            if last_hb == 0.0:
                dev_copy["status"] = "OFFLINE"
                dev_copy["secondsSinceHeartbeat"] = None
                dev_copy["lastHeartbeatFormatted"] = "Never"
            else:
                elapsed = round(now - last_hb, 1)
                dev_copy["secondsSinceHeartbeat"] = elapsed
                dev_copy["lastHeartbeatFormatted"] = datetime.fromtimestamp(last_hb).strftime("%H:%M:%S")
                
                # Dynamic health check
                if elapsed > settings.HEARTBEAT_TIMEOUT_SECONDS * 2:
                    dev_copy["status"] = "OFFLINE"
                elif elapsed > settings.HEARTBEAT_TIMEOUT_SECONDS:
                    dev_copy["status"] = "DEGRADED"
                else:
                    dev_copy["status"] = "ONLINE"
                    
            results.append(dev_copy)
        return results

    def get_device(self, device_id: str) -> Optional[Dict[str, Any]]:
        devices = self.get_all_devices()
        for d in devices:
            if d["deviceId"] == device_id:
                return d
        return None

device_service = DeviceService()
