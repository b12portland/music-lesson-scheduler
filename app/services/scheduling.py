from datetime import datetime
from app.utils import eastern_now
from app import db
from app.models import LessonSlot, Booking, GlobalSettings


def check_and_update_slot_status(slot):
    """
    Called after every booking or cancellation.
    Transitions slot status based on current booking count.
    Does not revert a confirmed slot back to open if count drops below threshold.
    """
    count = slot.active_booking_count()

    if slot.status == "open" and count >= slot.min_threshold:
        slot.status = "confirmed"
        db.session.commit()
        return "confirmed"

    return slot.status


def process_auto_closes():
    """
    Run hourly. Close any open slots whose deadline has passed without reaching threshold.
    Returns list of slots that were closed.
    """
    settings = GlobalSettings.get()
    now = eastern_now()
    closed = []

    open_slots = LessonSlot.query.filter_by(status="open").all()
    for slot in open_slots:
        if now >= slot.deadline(settings):
            slot.status = "closed"
            db.session.commit()
            closed.append(slot)

    return closed


def process_reminders():
    """
    Run hourly. Send reminder emails for confirmed slots whose reminder time has passed
    but whose lesson hasn't happened yet and reminder hasn't been sent.
    """
    settings = GlobalSettings.get()
    now = eastern_now()
    reminded = []

    confirmed_slots = LessonSlot.query.filter_by(status="confirmed", reminder_sent=False).all()
    for slot in confirmed_slots:
        if slot.reminder_at(settings) <= now < slot.scheduled_at:
            from app.services.notifications import send_reminder_emails
            send_reminder_emails(slot)
            slot.reminder_sent = True
            db.session.commit()
            reminded.append(slot)

    return reminded


def notify_slot_changed(slot, changes):
    """
    Stub: called when a teacher edits a slot that already has signups.
    Currently does nothing — email notification is a potential future feature.
    """
    pass
