"""
Audio & Microphone Control REST Endpoints.
Enables switching between ESP32 remote I2S streaming and Host Laptop built-in microphone.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Dict, Any, List, Optional
import sounddevice as sd

from backend.services.audio_service import audio_service

router = APIRouter(prefix="/api/audio", tags=["Audio Controls"])

@router.get("/source")
def get_audio_source() -> Dict[str, Any]:
    """Get active primary audio source and status."""
    return audio_service.get_audio_source()

@router.get("/telemetry")
def get_audio_telemetry() -> Dict[str, Any]:
    """Get real-time audio and YAMNet inference telemetry."""
    return audio_service.latest_telemetry


@router.post("/source/select")
def select_audio_source(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """
    Select active audio ingestion source.
    Accepts: {"source": "HOST_LAPTOP_MIC"} or {"source": "ESP32_INMP441"}
    """
    source = payload.get("source", "HOST_LAPTOP_MIC")
    res = audio_service.set_audio_source(source)
    return {
        "status": "SUCCESS",
        "message": f"Active audio source switched to: {res['activeSource']}",
        **res
    }

@router.get("/mic/status")
def get_mic_status() -> Dict[str, Any]:
    """Get active status of host laptop microphone capture."""
    return audio_service.get_audio_source()

@router.post("/mic/start")
def start_laptop_mic(device_index: Optional[int] = Query(None)) -> Dict[str, Any]:
    """Activate host laptop internal microphone as main audio source."""
    success = audio_service.start_laptop_mic(device_index=device_index)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to initialize laptop microphone.")
    return {
        "status": "SUCCESS",
        "message": f"Laptop microphone activated using: {audio_service.laptop_mic_device}",
        "device": audio_service.laptop_mic_device,
        "activeSource": audio_service.active_source
    }

@router.post("/mic/stop")
def stop_laptop_mic() -> Dict[str, Any]:
    """Stop host laptop microphone capture."""
    audio_service.stop_laptop_mic()
    return {
        "status": "SUCCESS",
        "message": "Laptop microphone stopped.",
        "activeSource": audio_service.active_source
    }

@router.get("/devices")
def list_audio_devices() -> List[Dict[str, Any]]:
    """List available host hardware audio input devices."""
    devices = []
    try:
        all_devs = sd.query_devices()
        for idx, d in enumerate(all_devs):
            if d.get("max_input_channels", 0) > 0:
                devices.append({
                    "index": idx,
                    "name": d.get("name"),
                    "channels": d.get("max_input_channels"),
                    "defaultSampleRate": d.get("default_samplerate")
                })
    except Exception as e:
        devices.append({"index": -1, "name": f"Error: {e}", "channels": 0})
    return devices
