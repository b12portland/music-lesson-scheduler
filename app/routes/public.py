import uuid
from app.utils import eastern_now
from sqlalchemy import func
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from app import db
from app.models import LessonSlot, Booking, GlobalSettings
from app.services.scheduling import check_and_update_slot_status
from app.services.notifications import (
    send_booking_confirmation_async,
    send_lesson_confirmed_async,
    notify_teacher_slot_confirmed_async,
    notify_teacher_new_booking_async,
    notify_teacher_booking_cancelled_async,
)

public_bp = Blueprint("public", __name__)


@public_bp.route("/")
def index():
    now = eastern_now()
    slots = (
        LessonSlot.query
        .filter(LessonSlot.status.in_(["open", "confirmed"]))
        .filter(LessonSlot.scheduled_at > now)
        .order_by(LessonSlot.scheduled_at)
        .all()
    )
    settings = GlobalSettings.get()
    return render_template("public/index.html", slots=slots, settings=settings, now=now)


@public_bp.route("/lessons/<int:slot_id>")
def slot_detail(slot_id):
    now = eastern_now()
    slot = LessonSlot.query.get_or_404(slot_id)
    # Only show upcoming open/confirmed slots to the public
    if slot.status not in ("open", "confirmed") or slot.scheduled_at <= now:
        abort(404)
    settings = GlobalSettings.get()
    return render_template("public/slot_detail.html", slot=slot, settings=settings, now=now)


@public_bp.route("/lessons/<int:slot_id>/book", methods=["POST"])
def book_slot(slot_id):
    now = eastern_now()
    slot = LessonSlot.query.get_or_404(slot_id)
    settings = GlobalSettings.get()

    if slot.status not in ("open", "confirmed") or slot.scheduled_at <= now:
        flash("This lesson is no longer available.", "error")
        return redirect(url_for("public.index"))

    if slot.spots_remaining() <= 0:
        flash("Sorry, this lesson is full.", "error")
        return redirect(url_for("public.slot_detail", slot_id=slot_id))

    client_name = request.form.get("client_name", "").strip()
    student_name = request.form.get("student_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip() or None

    if not all([client_name, student_name, email]):
        flash("Please fill in all required fields.", "error")
        return redirect(url_for("public.slot_detail", slot_id=slot_id))

    # Block duplicate: same email + same student name on the same slot
    duplicate = Booking.query.filter(
        Booking.slot_id == slot.id,
        Booking.status != "withdrawn",
        func.lower(Booking.email) == email,
        func.lower(Booking.student_name) == student_name.lower(),
    ).first()
    if duplicate:
        flash(f"{student_name} is already signed up for this lesson with this email address. "
              f"If you need to cancel, check your confirmation email for the cancellation link.", "error")
        return redirect(url_for("public.slot_detail", slot_id=slot_id))

    # Determine initial booking status
    initial_status = "confirmed" if slot.status == "confirmed" else "pending"

    booking = Booking(
        slot_id=slot.id,
        client_name=client_name,
        student_name=student_name,
        email=email,
        phone=phone,
        cancel_token=str(uuid.uuid4()),
        status=initial_status,
    )
    db.session.add(booking)
    db.session.commit()

    # Check if slot should now confirm
    previous_status = slot.status
    new_status = check_and_update_slot_status(slot)
    app = current_app._get_current_object()

    # Build cancel URL now while request context is active
    booking_cancel_url = url_for("public.cancel_booking", token=booking.cancel_token, _external=True)

    if previous_status == "open" and new_status == "confirmed":
        # Mark all pending bookings as confirmed
        for b in slot.bookings:
            if b.status == "pending":
                b.status = "confirmed"
        db.session.commit()
        # Build cancel URLs for all confirmed bookings while still in request context
        cancel_urls = {
            b.id: url_for("public.cancel_booking", token=b.cancel_token, _external=True)
            for b in slot.bookings if b.status == "confirmed"
        }
        send_lesson_confirmed_async(app, slot.id, cancel_urls)
        notify_teacher_slot_confirmed_async(app, slot.id)

    send_booking_confirmation_async(app, booking.id, slot.id, booking_cancel_url)
    notify_teacher_new_booking_async(app, slot.id, booking.id)

    return redirect(url_for("public.booking_confirmed", token=booking.cancel_token))


@public_bp.route("/booking/<token>/confirmed")
def booking_confirmed(token):
    booking = Booking.query.filter_by(cancel_token=token).first_or_404()
    return render_template(
        "public/booking_confirmed.html",
        booking=booking,
        slot=booking.slot,
    )


@public_bp.route("/cancel/<token>")
def cancel_booking(token):
    booking = Booking.query.filter_by(cancel_token=token).first_or_404()
    settings = GlobalSettings.get()

    if booking.status == "withdrawn":
        return render_template("public/cancel_result.html", result="already_cancelled", booking=booking)

    if not booking.cancellation_allowed(settings):
        return render_template("public/cancel_result.html", result="deadline_passed", booking=booking)

    return render_template("public/cancel_confirm.html", booking=booking, slot=booking.slot)


@public_bp.route("/cancel/<token>/confirm", methods=["POST"])
def confirm_cancellation(token):
    booking = Booking.query.filter_by(cancel_token=token).first_or_404()
    settings = GlobalSettings.get()

    if booking.status == "withdrawn":
        return render_template("public/cancel_result.html", result="already_cancelled", booking=booking)

    if not booking.cancellation_allowed(settings):
        return render_template("public/cancel_result.html", result="deadline_passed", booking=booking)

    booking.status = "withdrawn"
    db.session.commit()

    # If slot was confirmed and full, cancellation may reopen a spot — no status change needed,
    # the slot stays confirmed and spots_remaining() will reflect the new count automatically.

    app = current_app._get_current_object()
    notify_teacher_booking_cancelled_async(app, booking.slot_id, booking.id)

    return render_template("public/cancel_result.html", result="success", booking=booking)
