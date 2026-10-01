"""
Abstract Base Class for WhatsApp Notification Providers.
Defines required interface for Meta Graph API, Twilio, and Mock providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseWhatsAppProvider(ABC):
    @abstractmethod
    def send_message(self, recipient_phone: str, message_body: str) -> Dict[str, Any]:
        """
        Send a WhatsApp text/template message to a single recipient.
        Returns dict with:
        - success: bool
        - messageId: Optional[str]
        - error: Optional[str]
        - provider: str
        """
        pass

    @abstractmethod
    def send_batch(self, recipient_phones: List[str], message_body: str) -> List[Dict[str, Any]]:
        """
        Send emergency alert to a list of contacts.
        """
        pass
