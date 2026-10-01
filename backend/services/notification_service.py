"""
EchoSense Emergency Notification Service.
Manages emergency WhatsApp contact directory (max 5 contacts), formats objective
safety alerts for Critical events and SOS triggers, enforces anti-spam rate limits,
and tracks delivery outcomes across configured providers.
"""

import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from backend.events.event_model import EchoSenseEvent, EmergencyContact
from backend.notifications.whatsapp_base import BaseWhatsAppProvider
from backend.notifications.whatsapp_meta import MetaWhatsAppProvider
from backend.notifications.whatsapp_twilio import TwilioWhatsAppProvider
from backend.notifications.whatsapp_mock import MockWhatsAppProvider
from backend.config.settings import settings

logger = logging.getLogger("EchoSense.NotificationService")

class NotificationService:
    def __init__(self):
        self.provider: BaseWhatsAppProvider = self._init_provider()
        self.contacts: List[EmergencyContact] = [
            EmergencyContact(id="contact_1", name="Primary Caregiver", phoneNumber="+12345678901", enabled=True, priority=1, relationship="Caregiver"),
            EmergencyContact(id="contact_2", name="Family Member", phoneNumber="+12345678902", enabled=True, priority=2, relationship="Family"),
        ]
        self.last_notification_time = 0.0
        self.delivery_history: List[Dict[str, Any]] = []

    def _init_provider(self) -> BaseWhatsAppProvider:
        p_type = settings.WHATSAPP_PROVIDER.lower()
        if p_type == "meta":
            logger.info("Initializing Meta Cloud WhatsApp API provider.")
            return MetaWhatsAppProvider()
        elif p_type == "twilio":
            logger.info("Initializing Twilio WhatsApp API provider.")
            return TwilioWhatsAppProvider()
        else:
            logger.info("Initializing Local Mock WhatsApp provider.")
            return MockWhatsAppProvider()

    # --- Contact Management (Max 5) ---
    def get_contacts(self) -> List[EmergencyContact]:
        return sorted(self.contacts, key=lambda c: c.priority)

    def add_contact(self, contact: EmergencyContact) -> EmergencyContact:
        if len(self.contacts) >= settings.MAX_EMERGENCY_CONTACTS:
            raise ValueError(f"Maximum emergency contacts limit reached ({settings.MAX_EMERGENCY_CONTACTS}).")
        
        # Verify unique phone number
        for c in self.contacts:
            if c.phoneNumber.strip() == contact.phoneNumber.strip():
                raise ValueError("A contact with this phone number already exists.")
                
        self.contacts.append(contact)
        logger.info(f"Added emergency contact: {contact.name} ({contact.phoneNumber})")
        return contact

    def update_contact(self, contact_id: str, updated_data: Dict[str, Any]) -> Optional[EmergencyContact]:
        for idx, c in enumerate(self.contacts):
            if c.id == contact_id:
                c_dict = c.model_dump()
                c_dict.update(updated_data)
                updated_contact = EmergencyContact(**c_dict)
                self.contacts[idx] = updated_contact
                logger.info(f"Updated contact {contact_id}: {updated_contact.name}")
                return updated_contact
        return None

    def delete_contact(self, contact_id: str) -> bool:
        initial_len = len(self.contacts)
        self.contacts = [c for c in self.contacts if c.id != contact_id]
        deleted = len(self.contacts) < initial_len
        if deleted:
            logger.info(f"Deleted contact {contact_id}")
        return deleted

    # --- Message Formatting ---
    def format_event_message(self, event: EchoSenseEvent) -> str:
        """Construct objective, non-sensational emergency alert body."""
        time_str = datetime.fromtimestamp(event.timestamp).strftime("%H:%M:%S")
        device_label = "Host Laptop Microphone" if "LAPTOP" in (event.device or "").upper() else "ESP32 Wireless Unit (INMP441)"
        
        if event.category == "SOS":
            return (
                "🚨 *ECHOSENSE PHYSICAL EMERGENCY SOS*\n\n"
                "The user has activated the physical emergency SOS trigger.\n"
                "Immediate verification and assistance may be required.\n\n"
                f"🕒 *Time:* {time_str}\n"
                f"📡 *Source Node:* {device_label}\n"
                f"⚡ *Priority:* P0 (Immediate Override)\n\n"
                "👉 *Action:* Please contact or check on the user immediately."
            )
        else:
            conf_pct = int(event.confidence * 100)
            return (
                f"🚨 *ECHOSENSE SAFETY ALERT: {event.displayLabel.upper()}*\n\n"
                f"A verified acoustic alert condition was recognized by YAMNet AI.\n\n"
                f"🔊 *Detected Sound:* {event.rawLabel or event.displayLabel}\n"
                f"🎯 *Classification Confidence:* {conf_pct}%\n"
                f"🕒 *Timestamp:* {time_str}\n"
                f"📡 *Audio Source:* {device_label}\n"
                f"⚠️ *Severity:* {event.severity}\n\n"
                "👉 *Action:* Please verify the situation in the environment.\n"
                "_Automated assistive notification from EchoSense Safety Intelligence Hub._"
            )

    # --- Dispatch Logic ---
    def dispatch_alert(self, event: EchoSenseEvent, bypass_rate_limit: bool = False) -> Dict[str, Any]:
        """
        Send emergency notification to all enabled contacts.
        Enforces cooldown and updates event notification status.
        """
        now = time.time()
        
        # Enforce rate limit unless it's a physical SOS
        if not bypass_rate_limit and event.category != "SOS":
            if now - self.last_notification_time < settings.WHATSAPP_RATE_LIMIT_SECONDS:
                logger.warning(f"Notification suppressed by rate limit ({int(now - self.last_notification_time)}s < {settings.WHATSAPP_RATE_LIMIT_SECONDS}s)")
                event.notificationStatus = "RATE_LIMITED"
                return {"status": "RATE_LIMITED", "contactsNotified": 0}

        active_contacts = [c for c in self.contacts if c.enabled]
        if not active_contacts:
            logger.warning("No enabled emergency contacts configured. Notification skipped.")
            event.notificationStatus = "SKIPPED_NO_CONTACTS"
            return {"status": "SKIPPED_NO_CONTACTS", "contactsNotified": 0}

        message_body = self.format_event_message(event)
        recipients = [c.phoneNumber for c in active_contacts]
        
        logger.info(f"Dispatching emergency message to {len(recipients)} contacts for event: {event.displayLabel}")
        delivery_results = self.provider.send_batch(recipients, message_body)
        
        successful_dispatches = sum(1 for r in delivery_results if r.get("success", False))
        
        self.last_notification_time = now
        event.notificationStatus = "SENT" if successful_dispatches > 0 else "FAILED"
        event.contactsNotified = successful_dispatches
        event.totalContacts = len(active_contacts)
        
        summary = {
            "eventId": event.eventId,
            "timestamp": now,
            "displayLabel": event.displayLabel,
            "contactsTotal": len(active_contacts),
            "contactsSuccess": successful_dispatches,
            "results": delivery_results
        }
        self.delivery_history.insert(0, summary)
        if len(self.delivery_history) > 50:
            self.delivery_history.pop()
            
        return summary

    def send_test_notification(self) -> Dict[str, Any]:
        """Manually trigger test notification to all active contacts."""
        now = time.time()
        test_event = EchoSenseEvent(
            eventId=f"test_{int(now * 1000)}",
            timestamp=now,
            source="MANUAL_TEST",
            category="WARNING",
            rawLabel="Test Notification",
            displayLabel="Test Alert",
            confidence=1.0,
            severity="WARNING",
            priority=2,
            validated=True,
            device="DASHBOARD",
            notificationRequired=True
        )
        return self.dispatch_alert(test_event, bypass_rate_limit=True)

notification_service = NotificationService()
