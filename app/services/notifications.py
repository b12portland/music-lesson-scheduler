import smtplib
import logging
import threading
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from flask import current_app
from app import db
from app.services.calendar import generate_ics
from app.models import Booking, LessonSlot, GlobalSettings

logger = logging.getLogger(__name__)


def _run_in_background(app, fn, *args, **kwargs):
    """Run fn in a background thread with its own app context."""
    def run():
        with app.app_context():
            fn(*args, **kwargs)
    threading.Thread(target=run, daemon=True).start()


def send_booking_confirmation_async(app, booking_id, slot_id, cancel_url):
    def _do(booking_id, slot_id, cancel_url):
        booking = db.session.get(Booking, booking_id)
        slot = db.session.get(LessonSlot, slot_id)
        if booking and slot:
            send_booking_confirmation(booking, slot, cancel_url)
    _run_in_background(app, _do, booking_id, slot_id, cancel_url)


def send_lesson_confirmed_async(app, slot_id, cancel_urls):
    """cancel_urls: dict of {booking_id: cancel_url} built in request context."""
    def _do(slot_id, cancel_urls):
        slot = db.session.get(LessonSlot, slot_id)
        if slot:
            send_lesson_confirmed(slot, cancel_urls)
    _run_in_background(app, _do, slot_id, cancel_urls)


def notify_teacher_slot_confirmed_async(app, slot_id):
    def _do(slot_id):
        slot = db.session.get(LessonSlot, slot_id)
        if slot:
            notify_teacher_slot_confirmed(slot)
    _run_in_background(app, _do, slot_id)


def send_reminder_emails_async(app, slot_id):
    def _do(slot_id):
        slot = db.session.get(LessonSlot, slot_id)
        if slot:
            send_reminder_emails(slot)
    _run_in_background(app, _do, slot_id)


def notify_teacher_new_booking_async(app, slot_id, booking_id):
    def _do(slot_id, booking_id):
        slot = db.session.get(LessonSlot, slot_id)
        booking = db.session.get(Booking, booking_id)
        if slot and booking:
            notify_teacher_new_booking(slot, booking)
    _run_in_background(app, _do, slot_id, booking_id)


def notify_teacher_booking_cancelled_async(app, slot_id, booking_id):
    def _do(slot_id, booking_id):
        slot = db.session.get(LessonSlot, slot_id)
        booking = db.session.get(Booking, booking_id)
        if slot and booking:
            notify_teacher_booking_cancelled(slot, booking)
    _run_in_background(app, _do, slot_id, booking_id)


def _send(to, subject, body_html, attachment_name=None, attachment_data=None):
    cfg = current_app.config
    if not cfg.get("MAIL_USERNAME"):
        logger.warning("Email not configured — skipping send to %s", to)
        return False

    msg = MIMEMultipart("mixed")
    msg["From"] = cfg["MAIL_FROM"]
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body_html, "html"))

    if attachment_name and attachment_data:
        part = MIMEBase("text", "calendar", method="REQUEST")
        part.set_payload(attachment_data)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{attachment_name}"')
        msg.attach(part)

    try:
        with smtplib.SMTP(cfg["MAIL_SERVER"], cfg["MAIL_PORT"]) as server:
            if cfg.get("MAIL_USE_TLS"):
                server.starttls()
            server.login(cfg["MAIL_USERNAME"], cfg["MAIL_PASSWORD"])
            server.sendmail(cfg["MAIL_FROM"], to, msg.as_string())
        return True
    except Exception as e:
        logger.error("Failed to send email to %s: %s", to, e)
        return False


def send_booking_confirmation(booking, slot, cancel_url):
    """Email sent immediately after a client signs up."""
    settings = GlobalSettings.get()
    deadline = slot.deadline(settings)
    grace_deadline = booking.booked_at + timedelta(hours=24)
    cancel_by = max(deadline, grace_deadline)
    cancel_by_str = cancel_by.strftime('%A, %B %-d at %-I:%M %p')
    status_note = (
        "This lesson is already confirmed — you're in!"
        if slot.status == "confirmed"
        else f"This lesson will be confirmed once {slot.min_threshold} students have signed up. "
             f"Currently {slot.active_booking_count()} signed up."
    )
    ics = generate_ics(slot, booking)
    body = f"""
    <p>Hi {booking.client_name},</p>
    <p>You have signed up <strong>{booking.student_name}</strong> for:</p>
    <p><strong>{slot.title}</strong><br>
    {slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')}<br>
    {slot.location}</p>
    <p>{status_note}</p>
    <p>If you need to cancel, use this link — cancellations accepted until <strong>{cancel_by_str}</strong>:<br>
    <a href="{cancel_url}">{cancel_url}</a></p>
    <p>The calendar invite is attached.</p>
    """
    _send(booking.email, f"Booking received: {slot.title}", body,
          attachment_name="lesson.ics", attachment_data=ics)


def send_lesson_confirmed(slot, cancel_urls):
    """Email all confirmed bookings when a slot reaches its threshold.
    cancel_urls: dict of {booking_id: cancel_url}
    """
    settings = GlobalSettings.get()
    deadline = slot.deadline(settings)
    for booking in slot.active_bookings():
        if booking.status != "confirmed":
            continue
        cancel_url = cancel_urls.get(booking.id, "")
        ics = generate_ics(slot, booking)
        body = f"""
        <p>Hi {booking.client_name},</p>
        <p>Great news — <strong>{slot.title}</strong> is confirmed!</p>
        <p><strong>{slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')}</strong><br>
        {slot.location}</p>
        <p>Cancellations are accepted until {deadline.strftime('%A, %B %-d')}.<br>
        To cancel: <a href="{cancel_url}">{cancel_url}</a></p>
        <p>The calendar invite is attached.</p>
        """
        _send(booking.email, f"Lesson confirmed: {slot.title}", body,
              attachment_name="lesson.ics", attachment_data=ics)


def send_slot_closed(slot):
    """Email all pending bookings when a slot closes without confirming."""
    for booking in slot.bookings:
        if booking.status != "pending":
            continue
        body = f"""
        <p>Hi {booking.client_name},</p>
        <p>Unfortunately, <strong>{slot.title}</strong> scheduled for
        {slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')} did not reach
        the minimum number of sign-ups and will not be going ahead.</p>
        <p>We're sorry for the inconvenience.</p>
        """
        _send(booking.email, f"Lesson cancelled: {slot.title}", body)


def send_reminder_emails(slot):
    """Reminder email sent N days before a confirmed lesson."""
    settings = GlobalSettings.get()
    days = settings.reminder_days_before
    when = "tomorrow" if days == 1 else f"in {days} days"
    for booking in slot.active_bookings():
        body = f"""
        <p>Hi {booking.client_name},</p>
        <p>This is a reminder that <strong>{slot.title}</strong> is {when}.</p>
        <p><strong>{slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')}</strong><br>
        {slot.location}</p>
        <p>See you there!</p>
        """
        _send(booking.email, f"Reminder: {slot.title}", body)


def notify_teacher_slot_confirmed(slot):
    """Notify the teacher when a lesson slot confirms."""
    teacher = slot.teacher
    body = f"""
    <p>Hi {teacher.name},</p>
    <p><strong>{slot.title}</strong> on {slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')}
    has reached the minimum sign-ups and is now confirmed.</p>
    <p>{slot.active_booking_count()} students are signed up.</p>
    """
    _send(teacher.email, f"Lesson confirmed: {slot.title}", body)


def notify_teacher_new_booking(slot, booking):
    """Notify the teacher when a new client signs up."""
    teacher = slot.teacher
    count = slot.active_booking_count()
    body = f"""
    <p>Hi {teacher.name},</p>
    <p><strong>{booking.client_name}</strong> has signed up <strong>{booking.student_name}</strong>
    for <strong>{slot.title}</strong> on {slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')}.</p>
    <p>Signups: {count} / {slot.max_capacity} (minimum {slot.min_threshold} to confirm)</p>
    <p>Contact: {booking.email}{f" / {booking.phone}" if booking.phone else ""}</p>
    """
    _send(teacher.email, f"New signup: {slot.title}", body)


def notify_teacher_booking_cancelled(slot, booking):
    """Notify the teacher when a client cancels their booking."""
    teacher = slot.teacher
    count = slot.active_booking_count()
    body = f"""
    <p>Hi {teacher.name},</p>
    <p><strong>{booking.client_name}</strong> has cancelled their signup for
    <strong>{booking.student_name}</strong> in <strong>{slot.title}</strong>
    on {slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')}.</p>
    <p>Signups remaining: {count} / {slot.max_capacity}</p>
    """
    _send(teacher.email, f"Signup cancelled: {slot.title}", body)


def notify_teacher_slot_closed(slot):
    """Notify the teacher when a lesson auto-closes without reaching the threshold."""
    teacher = slot.teacher
    body = f"""
    <p>Hi {teacher.name},</p>
    <p><strong>{slot.title}</strong> scheduled for
    {slot.scheduled_at.strftime('%A, %B %-d at %-I:%M %p')} has been automatically closed
    because it did not reach the minimum of {slot.min_threshold} sign-ups
    ({slot.active_booking_count()} signed up).</p>
    <p>Clients who signed up have been notified.</p>
    """
    _send(teacher.email, f"Lesson auto-closed: {slot.title}", body)


