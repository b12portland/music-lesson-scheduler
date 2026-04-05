from functools import wraps
from datetime import datetime, timedelta
from app.utils import eastern_now
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from app import db
from app.models import LessonSlot, GlobalSettings
from app.services.notifications import (
    send_lesson_confirmed_async,
    notify_teacher_slot_confirmed_async,
    send_reminder_emails_async,
)

teacher_bp = Blueprint("teacher", __name__)


def teacher_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_teacher():
            abort(403)
        return f(*args, **kwargs)
    return decorated


@teacher_bp.route("/")
@login_required
@teacher_required
def dashboard():
    now = eastern_now()
    upcoming = (
        LessonSlot.query
        .filter(LessonSlot.scheduled_at > now)
        .filter(LessonSlot.status.in_(["open", "confirmed"]))
        .order_by(LessonSlot.scheduled_at)
        .all()
    )
    past = (
        LessonSlot.query
        .filter(
            db.or_(LessonSlot.scheduled_at <= now, LessonSlot.status == "closed")
        )
        .order_by(LessonSlot.scheduled_at.desc())
        .all()
    )
    return render_template("teacher/dashboard.html", upcoming=upcoming, past=past, now=now)


@teacher_bp.route("/slots/new", methods=["GET", "POST"])
@login_required
@teacher_required
def new_slot():
    settings = GlobalSettings.get()
    warning = None

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip() or None
        location = request.form.get("location", "").strip()
        scheduled_date = request.form.get("scheduled_date", "")
        scheduled_time = request.form.get("scheduled_time", "")
        duration_minutes = request.form.get("duration_minutes", "")
        min_threshold = request.form.get("min_threshold", "")
        max_capacity = request.form.get("max_capacity", "")
        confirmed_warning = request.form.get("confirmed_warning") == "1"

        errors = []
        if not all([title, location, scheduled_date, scheduled_time, duration_minutes, min_threshold, max_capacity]):
            errors.append("All required fields must be filled in.")

        try:
            scheduled_at = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
            duration_minutes = int(duration_minutes)
            min_threshold = int(min_threshold)
            max_capacity = int(max_capacity)
        except ValueError:
            errors.append("Invalid date, time, or numeric value.")
            return render_template("teacher/slot_form.html", settings=settings, warning=warning)

        if min_threshold > max_capacity:
            errors.append("Minimum signups cannot exceed maximum capacity.")

        deadline = scheduled_at - timedelta(days=settings.confirmation_required_before_days)
        now = eastern_now()

        short_notice = deadline <= now
        if short_notice and not confirmed_warning:
            days_until = (scheduled_at - now).days
            warning = (
                f"This lesson is only {days_until} day(s) away. With the current setting of "
                f"{settings.confirmation_required_before_days} days required before confirmation, "
                f"the sign-up deadline ({deadline.strftime('%B %-d')}) has already passed. "
                f"The lesson will auto-close within the hour unless the threshold is met."
            )
            return render_template("teacher/slot_form.html", settings=settings, warning=warning,
                                   form_data=request.form)

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("teacher/slot_form.html", settings=settings, warning=warning,
                                   form_data=request.form)

        slot = LessonSlot(
            teacher_id=current_user.id,
            title=title,
            description=description,
            location=location,
            scheduled_at=scheduled_at,
            duration_minutes=duration_minutes,
            min_threshold=min_threshold,
            max_capacity=max_capacity,
        )
        db.session.add(slot)
        db.session.commit()
        flash(f'Lesson "{title}" created.', "success")
        return redirect(url_for("teacher.slot_detail", slot_id=slot.id))

    return render_template("teacher/slot_form.html", settings=settings, warning=warning)


@teacher_bp.route("/slots/<int:slot_id>")
@login_required
@teacher_required
def slot_detail(slot_id):
    slot = db.session.get(LessonSlot, slot_id) or abort(404)
    settings = GlobalSettings.get()
    return render_template("teacher/slot_detail.html", slot=slot, settings=settings)


@teacher_bp.route("/slots/<int:slot_id>/edit", methods=["GET", "POST"])
@login_required
@teacher_required
def edit_slot(slot_id):
    slot = db.session.get(LessonSlot, slot_id) or abort(404)
    settings = GlobalSettings.get()
    existing_signups = slot.active_bookings()
    warning = None

    if request.method == "POST":
        confirmed_edit_warning = request.form.get("confirmed_edit_warning") == "1"

        if existing_signups and not confirmed_edit_warning:
            warning = "signups_exist"
            return render_template("teacher/slot_form.html", slot=slot, settings=settings,
                                   warning=warning, existing_signups=existing_signups,
                                   form_data=request.form)

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip() or None
        location = request.form.get("location", "").strip()
        scheduled_date = request.form.get("scheduled_date", "")
        scheduled_time = request.form.get("scheduled_time", "")
        duration_minutes = request.form.get("duration_minutes", "")
        min_threshold = request.form.get("min_threshold", "")
        max_capacity = request.form.get("max_capacity", "")

        try:
            scheduled_at = datetime.strptime(f"{scheduled_date} {scheduled_time}", "%Y-%m-%d %H:%M")
            duration_minutes = int(duration_minutes)
            min_threshold = int(min_threshold)
            max_capacity = int(max_capacity)
        except ValueError:
            flash("Invalid date, time, or numeric value.", "error")
            return render_template("teacher/slot_form.html", slot=slot, settings=settings,
                                   warning=warning, existing_signups=existing_signups)

        if min_threshold > max_capacity:
            flash("Minimum signups cannot exceed maximum capacity.", "error")
            return render_template("teacher/slot_form.html", slot=slot, settings=settings,
                                   warning=warning, existing_signups=existing_signups)

        slot.title = title
        slot.description = description
        slot.location = location
        slot.scheduled_at = scheduled_at
        slot.duration_minutes = duration_minutes
        slot.min_threshold = min_threshold
        slot.max_capacity = max_capacity
        db.session.commit()

        flash("Lesson updated.", "success")
        return redirect(url_for("teacher.slot_detail", slot_id=slot.id))

    return render_template("teacher/slot_form.html", slot=slot, settings=settings,
                           warning=warning, existing_signups=existing_signups)


@teacher_bp.route("/slots/<int:slot_id>/close", methods=["POST"])
@login_required
@teacher_required
def close_slot(slot_id):
    slot = db.session.get(LessonSlot, slot_id) or abort(404)
    slot.status = "closed"
    db.session.commit()
    flash(f'Lesson "{slot.title}" has been closed.', "success")
    return redirect(url_for("teacher.dashboard"))


@teacher_bp.route("/slots/<int:slot_id>/confirm", methods=["POST"])
@login_required
@teacher_required
def manual_confirm(slot_id):
    slot = db.session.get(LessonSlot, slot_id) or abort(404)
    if slot.status != "open":
        flash("Only open lessons can be manually confirmed.", "error")
        return redirect(url_for("teacher.slot_detail", slot_id=slot.id))
    if slot.active_booking_count() == 0:
        flash("Cannot confirm a lesson with no signups.", "error")
        return redirect(url_for("teacher.slot_detail", slot_id=slot.id))

    for b in slot.bookings:
        if b.status == "pending":
            b.status = "confirmed"
    slot.status = "confirmed"
    db.session.commit()

    app = current_app._get_current_object()
    cancel_urls = {
        b.id: url_for("public.cancel_booking", token=b.cancel_token, _external=True)
        for b in slot.bookings if b.status == "confirmed"
    }
    send_lesson_confirmed_async(app, slot.id, cancel_urls)
    notify_teacher_slot_confirmed_async(app, slot.id)

    flash(f'Lesson "{slot.title}" has been confirmed and clients have been notified.', "success")
    return redirect(url_for("teacher.slot_detail", slot_id=slot.id))


@teacher_bp.route("/slots/<int:slot_id>/send-reminders", methods=["POST"])
@login_required
@teacher_required
def manual_send_reminders(slot_id):
    slot = db.session.get(LessonSlot, slot_id) or abort(404)
    if slot.status != "confirmed":
        flash("Reminders can only be sent for confirmed lessons.", "error")
        return redirect(url_for("teacher.slot_detail", slot_id=slot.id))
    if slot.reminder_sent:
        flash("Reminders have already been sent for this lesson.", "error")
        return redirect(url_for("teacher.slot_detail", slot_id=slot.id))

    slot.reminder_sent = True
    db.session.commit()

    app = current_app._get_current_object()
    send_reminder_emails_async(app, slot.id)

    flash(f'Reminder emails are being sent for "{slot.title}".', "success")
    return redirect(url_for("teacher.slot_detail", slot_id=slot.id))
