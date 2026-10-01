"""
Mock WhatsApp Notification Provider.
Provides deterministic, zero-dependency local simulation for unit tests,
bench testing, and offline verification without incurring API charges or token expiries.
"""

import time
import logging
from typing import Dict, Any, List

from backend.notifications.whatsapp_base import BaseWhatsAppProvider

logger = logging.getLogger("EchoSense.WhatsApp.Mock")

class MockWhatsAppProvider(BaseWhatsAppProvider):
    def __init__(self):
        self.dispatched_messages: List[Dict[str, Any]] = []

    def send_message(self, recipient_phone: str, message_body: str) -> Dict[str, Any]:
        """Record message into mock dispatch buffer and log to stdout."""
        msg_id = f"mock_msg_{int(time.time() * 1000)}"
        record = {
            "success": True,
            "provider": "mock",
            "messageId": msg_id,
            "recipient": recipient_phone,
            "timestamp": time.time(),
            "body": message_body
        }
        self.dispatched_messages.append(record)
        logger.info(f"[MOCK WHATSAPP] Delivered to {recipient_phone}:\n{message_body}\n")
        return record

    def send_batch(self, recipient_phones: List[str], message_body: str) -> List[Dict[str, Any]]:
        return [self.send_message(p, message_body) for p in recipient_phones]

    def clear(self):
        self.dispatched_messages.clear()
