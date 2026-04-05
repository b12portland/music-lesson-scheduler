"""
Smoke tests: hit every route and assert no 500 errors.
These catch template errors, missing context variables, and broken imports.
"""
import uuid
import pytest
from datetime import datetime, timedelta
from app import db
from app.models import LessonSlot, Booking


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def slot(teacher):
    s = LessonSlot(
        teacher_id=teacher.id,
        title="Smoke Test Lesson",
        location="Studio A",
        scheduled_at=datetime.now() + timedelta(days=14),
        duration_minutes=60,
        min_threshold=3,
        max_capacity=5,
        status="open",
    )
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def confirmed_slot(teacher):
    s = LessonSlot(
        teacher_id=teacher.id,
        title="Confirmed Lesson",
        location="Studio B",
        scheduled_at=datetime.now() + timedelta(days=14),
        duration_minutes=60,
        min_threshold=1,
        max_capacity=5,
        status="confirmed",
    )
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture
def booking(slot):
    b = Booking(
        slot_id=slot.id,
        client_name="Jane Parent",
        student_name="Alice Student",
        email="jane@example.com",
        cancel_token=str(uuid.uuid4()),
        status="pending",
    )
    db.session.add(b)
    db.session.commit()
    return b


# ── Public routes ─────────────────────────────────────────────────────────────

def test_index(client):
    assert client.get("/").status_code == 200


def test_lesson_detail(client, slot):
    assert client.get(f"/lessons/{slot.id}").status_code == 200


def test_lesson_detail_not_found(client):
    assert client.get("/lessons/99999").status_code == 404


def test_book_slot_get_redirects(client, slot):
    # GET on a POST-only route should 405
    assert client.get(f"/lessons/{slot.id}/book").status_code == 405


def test_booking_confirmed_page(client, booking):
    assert client.get(f"/booking/{booking.cancel_token}/confirmed").status_code == 200


def test_booking_confirmed_bad_token(client):
    assert client.get("/booking/not-a-real-token/confirmed").status_code == 404


def test_cancel_page(client, booking):
    assert client.get(f"/cancel/{booking.cancel_token}").status_code == 200


def test_cancel_bad_token(client):
    assert client.get("/cancel/not-a-real-token").status_code == 404


# ── Auth routes ───────────────────────────────────────────────────────────────

def test_login_page(client):
    assert client.get("/login").status_code == 200


def test_logout_redirects(client):
    assert client.get("/logout").status_code == 302


# ── Teacher routes ────────────────────────────────────────────────────────────

def test_teacher_dashboard(superuser_client):
    assert superuser_client.get("/teacher/").status_code == 200


def test_teacher_new_slot_form(superuser_client):
    assert superuser_client.get("/teacher/slots/new").status_code == 200


def test_teacher_slot_detail(superuser_client, slot):
    assert superuser_client.get(f"/teacher/slots/{slot.id}").status_code == 200


def test_teacher_edit_slot_form(superuser_client, slot):
    assert superuser_client.get(f"/teacher/slots/{slot.id}/edit").status_code == 200


def test_teacher_routes_require_auth(client, slot):
    assert client.get("/teacher/").status_code == 302
    assert client.get(f"/teacher/slots/{slot.id}").status_code == 302
    assert client.get("/teacher/slots/new").status_code == 302


# ── Superuser routes ──────────────────────────────────────────────────────────

def test_superuser_dashboard(superuser_client):
    assert superuser_client.get("/admin/").status_code == 200


def test_superuser_new_teacher_form(superuser_client):
    assert superuser_client.get("/admin/teachers/new").status_code == 200


def test_superuser_routes_require_auth(client):
    assert client.get("/admin/").status_code == 302
