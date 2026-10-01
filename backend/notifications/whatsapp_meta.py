"""
Official Meta Cloud API (WhatsApp Business Graph API) Provider.
Sends direct WhatsApp emergency alerts using Meta's Cloud API endpoint.
"""

import logging
import requests
from typing import Dict, Any, List

from backend.notifications.whatsapp_base import BaseWhatsAppProvider
from backend.config.settings import settings

logger = logging.getLogger("EchoSense.WhatsApp.Meta")

class MetaWhatsAppProvider(BaseWhatsAppProvider):
    def __init__(self):
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.access_token = settings.WHATSAPP_ACCESS_TOKEN
        self.api_version = "v19.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"

    def send_message(self, recipient_phone: str, message_body: str) -> Dict[str, Any]:
        """Send message via Meta Cloud Graph API."""
        if not self.phone_number_id or not self.access_token:
            return {
                "success": False,
                "provider": "meta",
                "error": "Missing WHATSAPP_PHONE_NUMBER_ID or WHATSAPP_ACCESS_TOKEN",
                "recipient": recipient_phone
            }

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

        # Format number (remove + or dashes for Meta API)
        clean_phone = recipient_phone.replace("+", "").replace("-", "").replace(" ", "").strip()

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_body
            }
        }

        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=8.0)
            data = response.json()
            
            if response.status_code in (200, 201):
                msg_id = data.get("messages", [{}])[0].get("id", "unknown_id")
                logger.info(f"Meta WhatsApp dispatched successfully to {recipient_phone} (id: {msg_id})")
                return {
                    "success": True,
                    "provider": "meta",
                    "messageId": msg_id,
                    "recipient": recipient_phone
                }
            else:
                err_msg = data.get("error", {}).get("message", response.text)
                logger.error(f"Meta WhatsApp failed for {recipient_phone}: {err_msg}")
                return {
                    "success": False,
                    "provider": "meta",
                    "error": err_msg,
                    "recipient": recipient_phone
                }
        except Exception as e:
            logger.error(f"Exception calling Meta WhatsApp API: {e}")
            return {
                "success": False,
                "provider": "meta",
                "error": str(e),
                "recipient": recipient_phone
            }

    def send_batch(self, recipient_phones: List[str], message_body: str) -> List[Dict[str, Any]]:
        results = []
        for phone in recipient_phones:
            results.append(self.send_message(phone, message_body))
        return results
