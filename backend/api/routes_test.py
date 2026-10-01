"""
Development & Bench Testing REST Endpoints.
Allows developers and QA engineers to trigger synthetic hardware and alert states.
Clearly marked as DEVELOPMENT / TEST MODE.
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
import time

from backend.events.event_manager import event_manager
from backend.services.device_service import device_service
from backend.services.notification_service import notification_service
from backend.api.websocket_hub import ws_hub

router = APIRouter(prefix="/api/test", tags=["Development Testing"])

@router.post("/trigger")
def trigger_dev_test(payload: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Execute synthetic bench test actions."""
    action = payload.get("action", "").upper().strip()
    now = time.time()
    
    if action == "TEST_NORMAL":
        event = event_manager.reset_alert()
        return {"action": action, "result": "Normal state restored", "event": event.model_dump()}
        
    elif action == "TEST_WARNING":
        evt_dict = {
            "eventId": f"test_warn_{int(now * 1000)}",
            "source": "MANUAL_TEST",
            "category": "DOORBELL",
            "rawLabel": "Doorbell",
            "displayLabel": "Doorbell",
            "confidence": 0.88,
            "severity": "WARNING",
            "priority": 2,
            "validated": True,
            "device": "DEV_BENCH",
            "notificationRequired": False,
            "rgbColor": [255, 200, 0],
            "rgbMode": "YELLOW_PULSE",
            "lcdLine1": "SOUND DETECTED",
            "lcdLine2": "Doorbell",
            "buzzerPattern": "SHORT_BEEP"
        }
        event = event_manager.dispatch_validated_event(evt_dict)
        return {"action": action, "result": "Warning state dispatched", "event": event.model_dump() if event else None}
        
    elif action in ("TEST_CRITICAL", "TEST_GLASS_BREAK"):
        evt_dict = {
            "eventId": f"test_glass_{int(now * 1000)}",
            "source": "MANUAL_TEST",
            "category": "GLASS_BREAK",
            "rawLabel": "Glass, Shatter",
            "displayLabel": "Possible Glass Break",
            "confidence": 0.92,
            "severity": "CRITICAL",
            "priority": 1,
            "validated": True,
            "device": "DEV_BENCH",
            "notificationRequired": True,
            "rgbColor": [255, 30, 60],
            "rgbMode": "GLASS_SPARKLE",
            "lcdLine1": "WARNING",
            "lcdLine2": "Glass Break",
            "buzzerPattern": "CRITICAL_ALARM"
        }
        event = event_manager.dispatch_validated_event(evt_dict)
        return {"action": action, "result": "Critical Glass Break alert dispatched", "event": event.model_dump() if event else None}

    elif action in ("TEST_SMOKE_ALARM", "TEST_ALARM"):
        evt_dict = {
            "eventId": f"test_smoke_{int(now * 1000)}",
            "source": "MANUAL_TEST",
            "category": "SMOKE_FIRE_ALARM",
            "rawLabel": "Smoke detector, smoke alarm",
            "displayLabel": "Smoke / Fire Alarm Detected",
            "confidence": 0.94,
            "severity": "CRITICAL",
            "priority": 1,
            "validated": True,
            "device": "DEV_BENCH",
            "notificationRequired": True,
            "rgbColor": [255, 0, 0],
            "rgbMode": "RED_STROBE",
            "lcdLine1": "CRITICAL ALERT",
            "lcdLine2": "Smoke Detector",
            "buzzerPattern": "CRITICAL_ALARM"
        }
        event = event_manager.dispatch_validated_event(evt_dict)
        return {"action": action, "result": "Critical Smoke Alarm alert dispatched", "event": event.model_dump() if event else None}

    elif action in ("TEST_DISTRESS", "TEST_SCREAM"):
        evt_dict = {
            "eventId": f"test_distress_{int(now * 1000)}",
            "source": "MANUAL_TEST",
            "category": "DISTRESS",
            "rawLabel": "Screaming, Shout",
            "displayLabel": "Distress / Screaming Detected",
            "confidence": 0.88,
            "severity": "CRITICAL",
            "priority": 1,
            "validated": True,
            "device": "DEV_BENCH",
            "notificationRequired": True,
            "rgbColor": [255, 0, 0],
            "rgbMode": "RED_PULSE",
            "lcdLine1": "CRITICAL ALERT",
            "lcdLine2": "Distress Sound",
            "buzzerPattern": "ALARM_BURST"
        }
        event = event_manager.dispatch_validated_event(evt_dict)
        return {"action": action, "result": "Critical Distress alert dispatched", "event": event.model_dump() if event else None}

    elif action == "TEST_BABY_CRY":
        evt_dict = {
            "eventId": f"test_cry_{int(now * 1000)}",
            "source": "MANUAL_TEST",
            "category": "DISTRESS",
            "rawLabel": "Baby cry, infant cry",
            "displayLabel": "Baby Cry / Infant Distress",
            "confidence": 0.86,
            "severity": "CRITICAL",
            "priority": 1,
            "validated": True,
            "device": "DEV_BENCH",
            "notificationRequired": True,
            "rgbColor": [255, 0, 0],
            "rgbMode": "RED_PULSE",
            "lcdLine1": "CRITICAL ALERT",
            "lcdLine2": "Baby Crying",
            "buzzerPattern": "ALARM_BURST"
        }
        event = event_manager.dispatch_validated_event(evt_dict)
        return {"action": action, "result": "Baby Crying alert dispatched", "event": event.model_dump() if event else None}

    elif action == "TEST_DOG_BARK":
        evt_dict = {
            "eventId": f"test_bark_{int(now * 1000)}",
            "source": "MANUAL_TEST",
            "category": "DOG_BARK",
            "rawLabel": "Dog, Bark",
            "displayLabel": "Dog Bark",
            "confidence": 0.88,
            "severity": "WARNING",
            "priority": 2,
            "validated": True,
            "device": "DEV_BENCH",
            "notificationRequired": False,
            "rgbColor": [175, 55, 255],
            "rgbMode": "PURPLE_GLOW",
            "lcdLine1": "SOUND DETECTED",
            "lcdLine2": "Dog Bark",
            "buzzerPattern": "MODERATE_BEEP"
        }
        event = event_manager.dispatch_validated_event(evt_dict)
        return {"action": action, "result": "Dog Bark dispatched with Violet LED & Moderate Beep", "event": event.model_dump() if event else None}

    elif action in ("TEST_WATER", "TEST_DOMESTIC_WATER"):
        evt_dict = {
            "eventId": f"test_water_{int(now * 1000)}",
            "source": "MANUAL_TEST",
            "category": "DOMESTIC_WATER",
            "rawLabel": "Water tap, faucet",
            "displayLabel": "Water Running / Domestic Flow",
            "confidence": 0.90,
            "severity": "WARNING",
            "priority": 2,
            "validated": True,
            "device": "DEV_BENCH",
            "notificationRequired": False,
            "rgbColor": [0, 220, 255],
            "rgbMode": "CYAN_BREATH",
            "lcdLine1": "SOUND DETECTED",
            "lcdLine2": "Water Running",
            "buzzerPattern": "MODERATE_BEEP"
        }
        event = event_manager.dispatch_validated_event(evt_dict)
        return {"action": action, "result": "Water Running dispatched with Aquamarine Cyan & Moderate Beep", "event": event.model_dump() if event else None}

    elif action == "TEST_SOS":
        event = event_manager.trigger_sos(source="DEV_BENCH_TEST")
        return {"action": action, "result": "SOS state dispatched", "event": event.model_dump()}

    elif action == "TEST_ESP32":
        # Simulate ESP32 heartbeat
        dev = device_service.record_heartbeat({
            "deviceId": "ESP32_SENSE_01",
            "uptime": 3600,
            "rssi": -55,
            "firmwareVersion": "1.0.0",
            "sensors": {"inmp441": "HEALTHY", "sosButton": "READY"}
        })
        return {"action": action, "result": "ESP32 heartbeat simulated", "device": dev}

    elif action == "TEST_ESP8266":
        # Simulate ESP8266 heartbeat
        dev = device_service.record_heartbeat({
            "deviceId": "ESP8266_ALERT_01",
            "uptime": 3600,
            "rssi": -52,
            "firmwareVersion": "1.0.0",
            "actuators": {"rgbRing": "ACTIVE", "buzzer": "READY"}
        })
        return {"action": action, "result": "ESP8266 heartbeat simulated", "device": dev}

    elif action in ("TEST_BUZZER", "TEST_MODERATE_BUZZER"):
        from backend.events.event_model import EchoSenseEvent
        test_evt = EchoSenseEvent(
            eventId=f"test_buzzer_{int(now * 1000)}",
            displayLabel="Moderate Buzzer Test",
            rgbColor=[255, 185, 0],
            rgbMode="YELLOW_PULSE",
            buzzerPattern="MODERATE_BEEP",
            priority=2,
            severity="WARNING"
        )
        ws_hub.broadcast_event_state(test_evt)
        return {"action": action, "result": "Wise Moderate Beep command sent to ESP8266"}

    elif action == "TEST_CRITICAL_BUZZER":
        from backend.events.event_model import EchoSenseEvent
        test_evt = EchoSenseEvent(
            eventId=f"test_crit_buzzer_{int(now * 1000)}",
            displayLabel="Critical Buzzer Alarm",
            rgbColor=[255, 0, 0],
            rgbMode="RED_STROBE",
            buzzerPattern="CRITICAL_ALARM",
            priority=1,
            severity="CRITICAL"
        )
        ws_hub.broadcast_event_state(test_evt)
        return {"action": action, "result": "Critical Alarm Burst command sent to ESP8266"}

    elif action == "TEST_LED":
        from backend.events.event_model import EchoSenseEvent
        test_evt = EchoSenseEvent(
            eventId=f"test_led_{int(now * 1000)}",
            displayLabel="RGB Ring Test",
            rgbColor=[0, 255, 255],
            rgbMode="CYAN_PULSE",
            buzzerPattern="OFF",
            priority=3,
            severity="INFO"
        )
        ws_hub.broadcast_event_state(test_evt)
        return {"action": action, "result": "RGB pulse pattern sent to Alert Unit"}

    elif action == "TEST_STROBE":
        from backend.events.event_model import EchoSenseEvent
        test_evt = EchoSenseEvent(
            eventId=f"test_strobe_{int(now * 1000)}",
            displayLabel="Emergency Strobe Test",
            rgbColor=[255, 0, 100],
            rgbMode="EMERGENCY_STROBE",
            buzzerPattern="ALARM_BURST",
            priority=1,
            severity="CRITICAL"
        )
        ws_hub.broadcast_event_state(test_evt)
        return {"action": action, "result": "Emergency visual strobe sent to Alert Unit"}

    elif action == "TEST_WHATSAPP":
        res = notification_service.send_test_notification()
        return {"action": action, "result": "WhatsApp test dispatched", "details": res}

    elif action in ("TEST_CUSTOM_COLOR", "SET_LED_STATE"):
        from backend.events.event_model import EchoSenseEvent
        rgb = payload.get("rgbColor", [0, 255, 80])
        mode = payload.get("rgbMode", "GREEN_SOLID")
        label = payload.get("displayLabel", "Custom LED Test")
        priority = payload.get("priority", 3)
        buzzer = payload.get("buzzerPattern", "OFF")
        severity = payload.get("severity", "INFO" if priority >= 3 else ("WARNING" if priority == 2 else "CRITICAL"))
        
        test_evt = EchoSenseEvent(
            eventId=f"test_led_{int(now * 1000)}",
            displayLabel=label,
            rgbColor=rgb,
            rgbMode=mode,
            buzzerPattern=buzzer,
            priority=priority,
            severity=severity
        )
        ws_hub.broadcast_event_state(test_evt)
        return {"action": action, "result": f"LED state {mode} dispatched", "event": test_evt.model_dump()}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown test action: {action}")
