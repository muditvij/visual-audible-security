"""
Status & Configuration REST Endpoints.
"""

import time
from fastapi import APIRouter
from typing import Dict, Any

from backend.config.settings import settings
from backend.services.device_service import device_service
from backend.services.notification_service import notification_service
from backend.services.audio_service import audio_service

router = APIRouter(prefix="/api", tags=["Status"])

START_TIME = time.time()

import socket

def get_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "192.168.29.19"

@router.get("/status")
def get_system_status() -> Dict[str, Any]:
    """Overall system operational status."""
    devices = device_service.get_all_devices()
    esp32_dev = next((d for d in devices if d["type"] == "ESP32"), None)
    esp8266_dev = next((d for d in devices if d["type"] == "ESP8266"), None)
    
    contacts = notification_service.get_contacts()
    active_contacts = sum(1 for c in contacts if c.enabled)
    lan_ip = get_lan_ip()

    return {
        "system": "EchoSense",
        "version": "1.2.0",
        "uptimeSeconds": int(time.time() - START_TIME),
        "network": {
            "lanIp": lan_ip,
            "port": settings.SERVER_PORT,
            "mobileUrl": f"http://{lan_ip}:{settings.SERVER_PORT}"
        },
        "backend": {
            "status": "RUNNING",
            "host": settings.SERVER_HOST,
            "port": settings.SERVER_PORT
        },
        "classifier": {
            "status": "RUNNING" if audio_service.is_running else "STOPPED",
            "model": "YAMNet",
            "sampleRate": settings.AUDIO_SAMPLE_RATE,
            "isOfflineFallback": getattr(audio_service.classifier.classifier, "is_offline_fallback", False)
        },
        "microphone": {
            "status": "ACTIVE" if esp32_dev and esp32_dev["status"] == "ONLINE" else "WAITING_STREAM",
            "sampleRate": settings.AUDIO_SAMPLE_RATE,
            "bufferSeconds": audio_service.buffer.get_metrics().get("bufferedSeconds", 0.0)
        },
        "devices": {
            "esp32": esp32_dev["status"] if esp32_dev else "OFFLINE",
            "esp8266": esp8266_dev["status"] if esp8266_dev else "OFFLINE"
        },
        "notificationService": {
            "provider": settings.WHATSAPP_PROVIDER,
            "totalContacts": len(contacts),
            "activeContacts": active_contacts
        }
    }

@router.get("/network")
def get_network_info() -> Dict[str, Any]:
    """Retrieve host LAN IP address and mobile access URL."""
    lan_ip = get_lan_ip()
    port = settings.SERVER_PORT
    return {
        "lanIp": lan_ip,
        "port": port,
        "mobileUrl": f"http://{lan_ip}:{port}",
        "localUrl": f"http://localhost:{port}"
    }

@router.get("/config")
def get_config() -> Dict[str, Any]:
    """Retrieve operational thresholds and settings."""
    return {
        "confidenceLow": settings.YAMNET_CONFIDENCE_LOW,
        "confidenceValid": settings.YAMNET_CONFIDENCE_VALID,
        "confidenceHigh": settings.YAMNET_CONFIDENCE_HIGH,
        "temporalRequiredConfirmations": settings.TEMPORAL_REQUIRED_CONFIRMATIONS,
        "temporalValidationWindows": settings.TEMPORAL_VALIDATION_WINDOWS,
        "eventCooldownSeconds": settings.EVENT_COOLDOWN_SECONDS,
        "whatsappProvider": settings.WHATSAPP_PROVIDER,
        "maxContacts": settings.MAX_EMERGENCY_CONTACTS
    }
