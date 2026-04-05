"""
Tests that the teacher receives an email in each scenario where they should.

Patches _send to avoid real SMTP and _run_in_background to run synchronously
so background-threaded notifications complete before assertions.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

from app import db
from app.models import LessonSlot, Booking
from app.services.notifications import notify_teacher_slot_closed

from tests.conftest import SUPERUSER_EMAIL


def _sync_background(app, fn, *args, **kwargs):
    """Replacement for _run_in_background that runs synchronously in tests."""
    fn(*args, **kwargs)


def teacher_email_was_sent(mock_send, teacher_email=SUPERUSER_EMAIL):
    """Return True if _send was called with the teacher's email as recipient."""
    return any(c.args[0] == teacher_email for c in mock_send.call_args_list)


BOOK_FORM = {
    "client_name": "Jane Parent",
    "student_name": "Alice Student",
    "email": "jane@example.com",
    "phone": "",
}


@patch("app.services.notifications._run_in_background", side_effect=_sync_background)
@patch("app.services.notifications._send")
def test_teacher_notified_on_new_signup(mock_send, mock_bg, client, open_slot):
    client.post(f"/lessons/{open_slot.id}/book", data=BOOK_FORM)
    assert teacher_email_was_sent(mock_send), "Teacher should be emailed when a client signs up"


@patch("app.services.notifications._run_in_background", side_effect=_sync_background)
@patch("app.services.notifications._send")
def test_teacher_notified_on_signup_cancelled(mock_send, mock_bg, client, open_slot):
    client.post(f"/lessons/{open_slot.id}/book", data=BOOK_FORM)
    mock_send.reset_mock()

    booking = Booking.query.filter_by(email="jane@example.com").first()
    client.post(f"/cancel/{booking.cancel_token}/confirm")

    assert teacher_email_was_sent(mock_send), "Teacher should be emailed when a signup is cancelled"


@patch("app.services.notifications._run_in_background", side_effect=_sync_background)
@patch("app.services.notifications._send")
def test_teacher_notified_on_auto_confirm(mock_send, mock_bg, client, teacher, app):
    """Slot with min_threshold=1 confirms on the first signup."""
    slot = LessonSlot(
        teacher_id=teacher.id,
        title="Auto-confirm Lesson",
        location="Studio B",
        scheduled_at=datetime.now() + timedelta(days=14),
        duration_minutes=60,
        min_threshold=1,
        max_capacity=5,
        status="open",
    )
    db.session.add(slot)
    db.session.commit()

    client.post(f"/lessons/{slot.id}/book", data=BOOK_FORM)

    assert teacher_email_was_sent(mock_send), "Teacher should be emailed when a lesson auto-confirms"


@patch("app.services.notifications._run_in_background", side_effect=_sync_background)
@patch("app.services.notifications._send")
def test_teacher_notified_on_manual_confirm(mock_send, mock_bg, superuser_client, open_slot):
    # Add a booking so manual confirm is allowed
    booking = Booking(
        slot_id=open_slot.id,
        client_name="Jane Parent",
        student_name="Alice Student",
        email="jane@example.com",
        cancel_token="test-token-manual",
        status="pending",
    )
    db.session.add(booking)
    db.session.commit()

    superuser_client.post(f"/teacher/slots/{open_slot.id}/confirm")

    assert teacher_email_was_sent(mock_send), "Teacher should be emailed when a lesson is manually confirmed"


@patch("app.services.notifications._send")
def test_teacher_notified_on_auto_close(mock_send, app, teacher):
    """Slot whose deadline has passed without reaching threshold should notify teacher when closed."""
    slot = LessonSlot(
        teacher_id=teacher.id,
        title="Underfull Lesson",
        location="Studio C",
        scheduled_at=datetime.now() + timedelta(days=1),
        duration_minutes=60,
        min_threshold=3,
        max_capacity=5,
        status="open",
    )
    db.session.add(slot)
    db.session.commit()

    # Call the notification directly (auto-close runs in the scheduler job)
    notify_teacher_slot_closed(slot)

    assert teacher_email_was_sent(mock_send), "Teacher should be emailed when a lesson auto-closes"
