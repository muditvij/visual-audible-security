"""
Central Event Manager & Priority Arbiter.
Controls event lifecycle, priority-based state overrides, notification triggers,
and historical logging for the EchoSense ecosystem.
"""

import time
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable

from backend.events.event_model import EchoSenseEvent
from backend.config.settings import settings

logger = logging.getLogger("EchoSense.EventManager")

class EventManager:
    def __init__(self):
        self.events_history: List[EchoSenseEvent] = []
        self.max_history_size = 200
        
        # Currently active output state
        self.active_event: Optional[EchoSenseEvent] = None
        self.active_event_start_time: float = 0.0
        
        # Callbacks for dispatch
        self.on_state_change_callbacks: List[Callable[[EchoSenseEvent], None]] = []
        self.on_notification_callbacks: List[Callable[[EchoSenseEvent], None]] = []

    def register_state_listener(self, cb: Callable[[EchoSenseEvent], None]):
        """Register listener for device/UI state updates."""
        self.on_state_change_callbacks.append(cb)

    def register_notification_listener(self, cb: Callable[[EchoSenseEvent], None]):
        """Register listener for critical WhatsApp notifications."""
        self.on_notification_callbacks.append(cb)

    def trigger_sos(self, source: str = "ESP32_PHYSICAL_BUTTON") -> EchoSenseEvent:
        """
        Highest-priority immediate SOS trigger.
        Bypasses ML audio pipeline completely.
        Overrides any existing sound event state.
        """
        now = time.time()
        evt_id = f"sos_{int(now * 1000)}"
        time_str = datetime.fromtimestamp(now).strftime("%H:%M:%S")
        
        event = EchoSenseEvent(
            eventId=evt_id,
            timestamp=now,
            formattedTime=time_str,
            source=source,
            category="SOS",
            rawLabel="Emergency Button",
            displayLabel="PHYSICAL EMERGENCY SOS",
            confidence=1.0,
            severity="SOS",
            priority=0,
            validated=True,
            device="ESP32_BUTTON",
            notificationRequired=True,
            notificationStatus="PENDING",
            rgbColor=[255, 0, 128],       # Fast Red/Purple strobe
            rgbMode="EMERGENCY_STROBE",
            lcdLine1="!!! SOS !!!",
            lcdLine2="HELP NEEDED",
            buzzerPattern="SOS_ALARM"
        )
        
        logger.warning(f"🚨 PHYSICAL SOS EVENT TRIGGERED by {source}!")
        self._set_active_event(event, is_sos=True)
        return event

    def dispatch_validated_event(self, event_dict: Dict[str, Any]) -> Optional[EchoSenseEvent]:
        """
        Process validated event from ML pipeline.
        Enforces strict priority arbitration:
        Lower priority sounds NEVER overwrite active SOS or higher-priority states.
        """
        now = time.time()
        time_str = datetime.fromtimestamp(now).strftime("%H:%M:%S")
        
        priority = event_dict.get("priority", 4)
        
        # Check active event priority
        if self.active_event is not None:
            # Active SOS cannot be overridden by audio events
            if self.active_event.priority == 0:
                logger.debug(f"Audio event '{event_dict.get('displayLabel')}' suppressed: Active SOS in progress.")
                return None
            # If current active alert has strictly higher priority and hasn't timed out
            if self.active_event.priority < priority:
                elapsed = now - self.active_event_start_time
                if elapsed < settings.EVENT_COOLDOWN_SECONDS:
                    logger.debug(f"Event '{event_dict.get('displayLabel')}' suppressed by higher priority '{self.active_event.displayLabel}'.")
                    return None

        event = EchoSenseEvent(
            eventId=event_dict.get("eventId", f"evt_{int(now * 1000)}"),
            timestamp=now,
            formattedTime=time_str,
            source=event_dict.get("source", "YAMNET"),
            category=event_dict.get("category", "NORMAL"),
            rawLabel=event_dict.get("rawLabel", ""),
            displayLabel=event_dict.get("displayLabel", "Monitoring"),
            confidence=event_dict.get("confidence", 0.0),
            severity=event_dict.get("severity", "NORMAL"),
            priority=priority,
            validated=event_dict.get("validated", True),
            device=event_dict.get("device", "ESP32_MIC"),
            notificationRequired=event_dict.get("notificationRequired", False),
            notificationStatus="PENDING" if event_dict.get("notificationRequired", False) else "SKIPPED",
            rgbColor=event_dict.get("rgbColor", [0, 100, 255]),
            rgbMode=event_dict.get("rgbMode", "BLUE_BREATH"),
            lcdLine1=event_dict.get("lcdLine1", "LISTENING..."),
            lcdLine2=event_dict.get("lcdLine2", "Monitoring"),
            buzzerPattern=event_dict.get("buzzerPattern", "OFF")
        )

        self._set_active_event(event)
        return event

    def _set_active_event(self, event: EchoSenseEvent, is_sos: bool = False):
        """Store in history and notify all subscribers."""
        self.active_event = event
        self.active_event_start_time = event.timestamp
        
        # Prepend to history
        self.events_history.insert(0, event)
        if len(self.events_history) > self.max_history_size:
            self.events_history.pop()

        # 1. Update IoT devices & Frontend UI
        for cb in self.on_state_change_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

        # 2. Trigger notifications if required
        if event.notificationRequired:
            for ncb in self.on_notification_callbacks:
                try:
                    ncb(event)
                except Exception as e:
                    logger.error(f"Error in notification callback: {e}")

    def reset_alert(self) -> EchoSenseEvent:
        """Reset active emergency or warning state back to normal listening."""
        now = time.time()
        time_str = datetime.fromtimestamp(now).strftime("%H:%M:%S")
        
        event = EchoSenseEvent(
            eventId=f"reset_{int(now * 1000)}",
            timestamp=now,
            formattedTime=time_str,
            source="MANUAL_RESET",
            category="NORMAL",
            rawLabel="Reset",
            displayLabel="System Ready",
            confidence=1.0,
            severity="NORMAL",
            priority=4,
            validated=True,
            device="DASHBOARD",
            notificationRequired=False,
            notificationStatus="SKIPPED",
            rgbColor=[255, 255, 255],  # Pure Ambient White
            rgbMode="WHITE_BREATH",
            lcdLine1="ECHOSENSE",
            lcdLine2="System Ready",
            buzzerPattern="OFF"
        )
        
        self.active_event = None
        self.active_event_start_time = 0.0
        
        for cb in self.on_state_change_callbacks:
            try:
                cb(event)
            except Exception as e:
                logger.error(f"Error notifying reset: {e}")
                
        return event

    def get_history(self, limit: int = 50, severity: Optional[str] = None) -> List[EchoSenseEvent]:
        """Fetch historical events with optional severity filter."""
        filtered = self.events_history
        if severity:
            filtered = [e for e in filtered if e.severity.upper() == severity.upper()]
        return filtered[:limit]

event_manager = EventManager()
