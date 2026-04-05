import bcrypt
from functools import wraps
from datetime import timedelta
from app.utils import eastern_now
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app import db
from app.models import User, GlobalSettings, LessonSlot

superuser_bp = Blueprint("superuser", __name__)


def superuser_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_superuser():
            abort(403)
        return f(*args, **kwargs)
    return decorated


@superuser_bp.route("/")
@login_required
@superuser_required
def dashboard():
    teachers = User.query.filter(User.role.in_(["teacher", "superuser"])).all()
    settings = GlobalSettings.get()
    return render_template("superuser/dashboard.html", teachers=teachers, settings=settings)


@superuser_bp.route("/teachers/new", methods=["GET", "POST"])
@login_required
@superuser_required
def new_teacher():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not all([name, email, password]):
            flash("All fields are required.", "error")
            return render_template("superuser/teacher_form.html")

        if User.query.filter_by(email=email).first():
            flash("A user with that email already exists.", "error")
            return render_template("superuser/teacher_form.html")

        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        teacher = User(name=name, email=email, password_hash=hashed, role="teacher")
        db.session.add(teacher)
        db.session.commit()
        flash(f"Teacher account created for {name}.", "success")
        return redirect(url_for("superuser.dashboard"))

    return render_template("superuser/teacher_form.html")


@superuser_bp.route("/teachers/<int:user_id>/reset-password", methods=["POST"])
@login_required
@superuser_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = request.form.get("new_password", "")
    if not new_password:
        flash("Password cannot be empty.", "error")
        return redirect(url_for("superuser.dashboard"))

    user.password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    db.session.commit()
    flash(f"Password updated for {user.name}.", "success")
    return redirect(url_for("superuser.dashboard"))


@superuser_bp.route("/settings", methods=["POST"])
@login_required
@superuser_required
def update_settings():
    settings = GlobalSettings.get()
    old_days = settings.confirmation_required_before_days

    try:
        new_days = int(request.form.get("confirmation_required_before_days", old_days))
        new_reminder = int(request.form.get("reminder_days_before", settings.reminder_days_before))
    except ValueError:
        flash("Invalid settings values.", "error")
        return redirect(url_for("superuser.dashboard"))

    # Check if the new confirmation_required_before_days would conflict with existing open slots
    if new_days != old_days:
        now = eastern_now()
        open_slots = LessonSlot.query.filter_by(status="open").all()
        conflicts = []
        for slot in open_slots:
            new_deadline = slot.scheduled_at - timedelta(days=new_days)
            if new_deadline <= now:
                conflicts.append(slot)

        if conflicts:
            conflict_list = ", ".join(f'"{s.title}" ({s.scheduled_at.strftime("%b %-d")})' for s in conflicts)
            flash(
                f"Warning: changing this setting would put the following open lessons past their "
                f"sign-up deadline immediately: {conflict_list}. "
                f"They will be auto-closed within the hour. Setting saved anyway.",
                "warning"
            )

    settings.confirmation_required_before_days = new_days
    settings.reminder_days_before = new_reminder
    db.session.commit()
    flash("Settings updated.", "success")
    return redirect(url_for("superuser.dashboard"))
