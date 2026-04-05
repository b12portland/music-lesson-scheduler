from app.models import LessonSlot
from app import db


def test_manual_confirm_rejected_with_no_signups(superuser_client, open_slot):
    """Confirming a lesson with zero signups should be rejected server-side."""
    response = superuser_client.post(
        f"/teacher/slots/{open_slot.id}/confirm",
        follow_redirects=True,
    )
    assert response.status_code == 200
    slot = LessonSlot.query.get(open_slot.id)
    assert slot.status == "open", "Slot should remain open when confirmed with no signups"
