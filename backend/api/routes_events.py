"""
Event & Emergency Alert REST Endpoints.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional

from backend.events.event_manager import event_manager
from backend.events.event_model import EchoSenseEvent
from backend.services.audio_service import audio_service

router = APIRouter(prefix="/api/events", tags=["Events"])

@router.get("")
def get_events(
    limit: int = Query(50, ge=1, le=200),
    severity: Optional[str] = Query(None)
) -> List[Dict[str, Any]]:
    """Retrieve historical event records."""
    events = event_manager.get_history(limit=limit, severity=severity)
    return [e.model_dump() for e in events]

@router.get("/live")
def get_live_state() -> Dict[str, Any]:
    """Retrieve instantaneous audio telemetry and validation progress."""
    active_alert = event_manager.active_event.model_dump() if event_manager.active_event else None
    return {
        "telemetry": audio_service.latest_telemetry,
        "activeAlert": active_alert
    }

@router.post("/sos")
def trigger_sos(source: str = "ESP32_PHYSICAL_BUTTON") -> Dict[str, Any]:
    """Immediate high-priority SOS emergency trigger."""
    event = event_manager.trigger_sos(source=source)
    return {
        "status": "SOS_ACTIVATED",
        "event": event.model_dump()
    }

@router.post("/reset")
def reset_alert() -> Dict[str, Any]:
    """Reset active alarm/warning state back to normal listening."""
    event = event_manager.reset_alert()
    return {
        "status": "ALERT_RESET",
        "event": event.model_dump()
    }
