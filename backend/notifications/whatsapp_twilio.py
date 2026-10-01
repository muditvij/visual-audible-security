"""
Twilio WhatsApp API Provider.
Enables emergency notification dispatch using Twilio's WhatsApp Messaging API.
"""

import logging
import requests
from requests.auth import HTTPBasicAuth
from typing import Dict, Any, List

from backend.notifications.whatsapp_base import BaseWhatsAppProvider
from backend.config.settings import settings

logger = logging.getLogger("EchoSense.WhatsApp.Twilio")

class TwilioWhatsAppProvider(BaseWhatsAppProvider):
    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.from_number = settings.TWILIO_WHATSAPP_FROM
        self.base_url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

    def send_message(self, recipient_phone: str, message_body: str) -> Dict[str, Any]:
        """Dispatch message via Twilio REST endpoint."""
        if not self.account_sid or not self.auth_token:
            return {
                "success": False,
                "provider": "twilio",
                "error": "Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN",
                "recipient": recipient_phone
            }

        to_formatted = f"whatsapp:{recipient_phone.strip()}" if not recipient_phone.startswith("whatsapp:") else recipient_phone
        from_formatted = f"whatsapp:{self.from_number.strip()}" if not self.from_number.startswith("whatsapp:") else self.from_number

        data = {
            "From": from_formatted,
            "To": to_formatted,
            "Body": message_body
        }

        try:
            response = requests.post(
                self.base_url,
                data=data,
                auth=HTTPBasicAuth(self.account_sid, self.auth_token),
                timeout=8.0
            )
            res_json = response.json()
            if response.status_code in (200, 201):
                sid = res_json.get("sid", "unknown_sid")
                logger.info(f"Twilio WhatsApp sent to {recipient_phone} (SID: {sid})")
                return {
                    "success": True,
                    "provider": "twilio",
                    "messageId": sid,
                    "recipient": recipient_phone
                }
            else:
                err = res_json.get("message", response.text)
                logger.error(f"Twilio WhatsApp error for {recipient_phone}: {err}")
                return {
                    "success": False,
                    "provider": "twilio",
                    "error": err,
                    "recipient": recipient_phone
                }
        except Exception as e:
            logger.error(f"Exception sending Twilio WhatsApp message: {e}")
            return {
                "success": False,
                "provider": "twilio",
                "error": str(e),
                "recipient": recipient_phone
            }

    def send_batch(self, recipient_phones: List[str], message_body: str) -> List[Dict[str, Any]]:
        return [self.send_message(p, message_body) for p in recipient_phones]
