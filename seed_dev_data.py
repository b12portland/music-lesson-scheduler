"""
Development seed script — creates 5 sample lessons with bookings.
Run manually: venv/bin/python seed_dev_data.py

Does NOT send any emails.
Safe to run multiple times — clears previously seeded data first.
"""

import sys
import uuid
from datetime import timedelta
from app import create_app, db
from app.models import LessonSlot, Booking, User
from app.utils import eastern_now

app = create_app()

SEED_TAG = "[SEED]"  # Prefix added to seeded slot titles so we can find and remove them

MIN_THRESHOLD = 3
MAX_CAPACITY = 5

SAMPLE_CLIENTS = [
    ("Alice Martin",   "Sophie Martin",   "alice@example.com",   "555-0101"),
    ("Bob Chen",       "Leo Chen",        "bob@example.com",     "555-0102"),
    ("Carol Davis",    "Mia Davis",       "carol@example.com",   "555-0103"),
    ("David Park",     "Noah Park",       "david@example.com",   "555-0104"),
    ("Eva Rossi",      "Luna Rossi",      "eva@example.com",     "555-0105"),
]

LESSONS = [
    {
        "days_ahead": 2,
        "title": f"{SEED_TAG} Beginner Guitar — Empty",
        "description": "Introduction to guitar for complete beginners. No experience needed.",
        "location": "123 Main St, Portland, OR",
        "duration_minutes": 60,
        "booking_count": 0,
        "status": "open",
        "label": "Empty (0 bookings)",
    },
    {
        "days_ahead": 9,
        "title": f"{SEED_TAG} Piano Theory — Below Threshold",
        "description": "Fundamentals of music theory taught through the piano. Suitable for beginners.",
        "location": "456 Oak Ave, Portland, OR",
        "duration_minutes": 60,
        "booking_count": 1,
        "status": "open",
        "label": "Below threshold (1 booking)",
    },
    {
        "days_ahead": 16,
        "title": f"{SEED_TAG} Violin Basics — At Threshold",
        "description": "First steps on the violin: posture, bow hold, and open strings.",
        "location": "789 Elm St, Portland, OR",
        "duration_minutes": 45,
        "booking_count": 3,
        "status": "confirmed",
        "label": "At threshold (3 bookings, confirmed)",
    },
    {
        "days_ahead": 23,
        "title": f"{SEED_TAG} Group Drumming — Full",
        "description": "High-energy group drumming session. All levels welcome.",
        "location": "321 Pine Rd, Portland, OR",
        "duration_minutes": 90,
        "booking_count": 5,
        "status": "confirmed",
        "label": "Full (5/5 bookings, confirmed)",
    },
    {
        "days_ahead": 30,
        "title": f"{SEED_TAG} Ukulele Fun — Above Threshold",
        "description": "Learn ukulele chords and strum along to popular songs.",
        "location": "654 Maple Dr, Portland, OR",
        "duration_minutes": 60,
        "booking_count": 4,
        "status": "confirmed",
        "label": "Above threshold, not full (4/5 bookings, confirmed)",
    },
]


def get_teacher():
    teacher = User.query.filter(User.role.in_(["teacher", "superuser"])).first()
    if not teacher:
        print("ERROR: No teacher or superuser account found. Log in and create one first.")
        sys.exit(1)
    return teacher


def clear_seeded_data():
    seeded = LessonSlot.query.filter(LessonSlot.title.like(f"{SEED_TAG}%")).all()
    for slot in seeded:
        Booking.query.filter_by(slot_id=slot.id).delete()
        db.session.delete(slot)
    db.session.commit()
    if seeded:
        print(f"Cleared {len(seeded)} previously seeded lesson(s).")


def seed():
    with app.app_context():
        clear_seeded_data()

        teacher = get_teacher()
        now = eastern_now()

        print(f"\nSeeding 5 lessons as teacher: {teacher.name} ({teacher.email})\n")

        for lesson in LESSONS:
            scheduled_at = now + timedelta(days=lesson["days_ahead"])
            scheduled_at = scheduled_at.replace(hour=10, minute=0, second=0, microsecond=0)

            slot = LessonSlot(
                teacher_id=teacher.id,
                title=lesson["title"],
                description=lesson["description"],
                location=lesson["location"],
                scheduled_at=scheduled_at,
                duration_minutes=lesson["duration_minutes"],
                min_threshold=MIN_THRESHOLD,
                max_capacity=MAX_CAPACITY,
                status=lesson["status"],
            )
            db.session.add(slot)
            db.session.flush()  # get slot.id before committing

            clients = SAMPLE_CLIENTS[: lesson["booking_count"]]
            for client_name, student_name, email, phone in clients:
                booking = Booking(
                    slot_id=slot.id,
                    client_name=client_name,
                    student_name=student_name,
                    email=email,
                    phone=phone,
                    cancel_token=str(uuid.uuid4()),
                    booked_at=now - timedelta(days=1),
                    status="confirmed" if lesson["status"] == "confirmed" else "pending",
                )
                db.session.add(booking)

            db.session.commit()
            print(f"  ✓ {lesson['days_ahead']:>2} days away — {lesson['label']}")
            print(f"       \"{lesson['title']}\"")
            print(f"        {scheduled_at.strftime('%A, %B %-d at %-I:%M %p')}\n")

        print("Done. No emails were sent.")
        print("Note: the 2-day lesson's signup deadline may have already passed")
        print("and could be auto-closed by the scheduler within the hour.\n")


if __name__ == "__main__":
    seed()
