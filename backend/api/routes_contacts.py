"""
Emergency Contact Management REST Endpoints.
Guarantees a strict maximum of 5 emergency contacts with complete CRUD operations.
"""

from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any

from backend.services.notification_service import notification_service
from backend.events.event_model import EmergencyContact
from backend.config.settings import settings

router = APIRouter(prefix="/api/contacts", tags=["Emergency Contacts"])

@router.get("")
def list_contacts() -> List[Dict[str, Any]]:
    """List all emergency contacts ordered by priority."""
    return [c.model_dump() for c in notification_service.get_contacts()]

@router.post("")
def add_contact(contact: EmergencyContact) -> Dict[str, Any]:
    """Add a new contact (Maximum 5 contacts allowed)."""
    try:
        new_c = notification_service.add_contact(contact)
        return {"status": "SUCCESS", "contact": new_c.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{contact_id}")
def update_contact(contact_id: str, updated_fields: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """Update contact details or toggle enabled state."""
    updated = notification_service.update_contact(contact_id, updated_fields)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"status": "SUCCESS", "contact": updated.model_dump()}

@router.delete("/{contact_id}")
def delete_contact(contact_id: str) -> Dict[str, Any]:
    """Remove emergency contact."""
    deleted = notification_service.delete_contact(contact_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Contact not found")
    return {"status": "SUCCESS", "deletedId": contact_id}

@router.post("/test")
def send_test_notification() -> Dict[str, Any]:
    """Dispatches a test notification to all enabled emergency contacts."""
    res = notification_service.send_test_notification()
    return {"status": "TEST_NOTIFICATION_SENT", "results": res}
