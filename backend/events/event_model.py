"""
EchoSense Event Data Models.
Standardized data structures shared by ML pipeline, database, WebSocket hub, and IoT nodes.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import time

class EchoSenseEvent(BaseModel):
    eventId: str
    timestamp: float = Field(default_factory=time.time)
    formattedTime: str = ""
    source: str = "YAMNET"  # YAMNET, ESP32_PHYSICAL_BUTTON, MANUAL_TEST
    category: str = "NORMAL"
    rawLabel: str = ""
    displayLabel: str = "Monitoring"
    confidence: float = 0.0
    severity: str = "NORMAL"  # SOS, CRITICAL, WARNING, INFO, NORMAL
    priority: int = 4         # 0 (SOS) to 4 (NORMAL)
    validated: bool = False
    device: str = "ESP32_MIC"
    notificationRequired: bool = False
    notificationStatus: str = "SKIPPED"  # PENDING, SENT, FAILED, SKIPPED, RATE_LIMITED
    contactsNotified: int = 0
    totalContacts: int = 0
    durationSeconds: float = 0.0
    rgbColor: List[int] = Field(default_factory=lambda: [0, 100, 255])
    rgbMode: str = "BLUE_BREATH"
    lcdLine1: str = "LISTENING..."
    lcdLine2: str = "Monitoring"
    buzzerPattern: str = "OFF"

class EmergencyContact(BaseModel):
    id: str
    name: str
    phoneNumber: str
    enabled: bool = True
    priority: int = 1
    relationship: str = "Caregiver"
    createdTimestamp: float = Field(default_factory=time.time)

class DeviceHeartbeatPayload(BaseModel):
    deviceId: str
    type: str = "ESP32"  # ESP32 or ESP8266
    uptime: int = 0
    rssi: int = -60
    firmwareVersion: str = "1.0.0"
    state: str = "RUNNING"
    sensors: Optional[Dict[str, Any]] = None
    actuators: Optional[Dict[str, Any]] = None
