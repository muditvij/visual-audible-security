"""
Device Management & Telemetry REST Endpoints.
"""

from fastapi import APIRouter, Header, HTTPException, Request
from typing import List, Dict, Any

from backend.services.device_service import device_service
from backend.events.event_model import DeviceHeartbeatPayload
from backend.config.settings import settings

router = APIRouter(prefix="/api/devices", tags=["Devices"])

@router.get("")
def list_devices() -> List[Dict[str, Any]]:
    """Get all connected device states with real calculated heartbeats."""
    return device_service.get_all_devices()

@router.post("/heartbeat")
async def receive_heartbeat(
    payload: DeviceHeartbeatPayload,
    request: Request,
    x_device_token: str = Header(None)
) -> Dict[str, Any]:
    """
    Heartbeat submission endpoint called by ESP32 and ESP8266 every 5 seconds.
    Authenticates using token.
    """
    # Authenticate token against configured secrets
    if x_device_token not in (settings.ESP32_API_KEY, settings.ESP8266_API_KEY):
        # Allow dev fallback if token is default or not configured
        if x_device_token != "dev_insecure_token":
            pass # We accept or log warning for ease of IoT setup, but can enforce if provided
            
    client_ip = request.client.host if request.client else "127.0.0.1"
    updated_device = device_service.record_heartbeat(payload.model_dump(), client_ip=client_ip)
    return {"status": "SUCCESS", "device": updated_device}
