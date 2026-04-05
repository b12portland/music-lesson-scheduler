from datetime import datetime
from app.utils import eastern_now
from flask_login import UserMixin
from app import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # superuser | teacher
    created_at = db.Column(db.DateTime, default=eastern_now)

    slots = db.relationship("LessonSlot", backref="teacher", lazy=True)

    def is_superuser(self):
        return self.role == "superuser"

    def is_teacher(self):
        return self.role in ("teacher", "superuser")


class LessonSlot(db.Model):
    __tablename__ = "lesson_slots"

    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    location = db.Column(db.String(300), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    max_capacity = db.Column(db.Integer, nullable=False)
    min_threshold = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="open")  # open | confirmed | closed
    reminder_sent = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=eastern_now)

    bookings = db.relationship("Booking", backref="slot", lazy=True)

    def active_bookings(self):
        return [b for b in self.bookings if b.status in ("pending", "confirmed")]

    def active_booking_count(self):
        return len(self.active_bookings())

    def spots_remaining(self):
        return self.max_capacity - self.active_booking_count()

    def signups_needed(self):
        return max(0, self.min_threshold - self.active_booking_count())

    def deadline(self, settings):
        """Signup/cancellation deadline derived from global settings."""
        from datetime import timedelta
        return self.scheduled_at - timedelta(days=settings.confirmation_required_before_days)

    def reminder_at(self, settings):
        from datetime import timedelta
        return self.scheduled_at - timedelta(days=settings.reminder_days_before)


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("lesson_slots.id"), nullable=False)
    client_name = db.Column(db.String(120), nullable=False)
    student_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(30), nullable=True)
    cancel_token = db.Column(db.String(64), unique=True, nullable=False)
    booked_at = db.Column(db.DateTime, default=eastern_now)
    status = db.Column(db.String(20), nullable=False, default="pending")  # pending | confirmed | withdrawn

    def cancellation_allowed(self, settings):
        """
        Cancellation allowed if EITHER:
        - The confirmation deadline hasn't passed yet, OR
        - It's been fewer than 24 hours since booking (24hr grace)
        """
        from datetime import timedelta
        now = eastern_now()
        within_grace = now < self.booked_at + timedelta(hours=24)
        before_deadline = now < self.slot.deadline(settings)
        return within_grace or before_deadline


class GlobalSettings(db.Model):
    __tablename__ = "global_settings"

    id = db.Column(db.Integer, primary_key=True)
    confirmation_required_before_days = db.Column(db.Integer, nullable=False, default=7)
    reminder_days_before = db.Column(db.Integer, nullable=False, default=1)

    @staticmethod
    def get():
        return GlobalSettings.query.first()
