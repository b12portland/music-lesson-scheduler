import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from app import create_app, db as _db
from app.models import LessonSlot, User

SUPERUSER_EMAIL = "test-admin@example.com"
SUPERUSER_PASSWORD = "testpassword"


@pytest.fixture
def app():
    env_overrides = {
        "SUPERUSER_EMAIL": SUPERUSER_EMAIL,
        "SUPERUSER_PASSWORD": SUPERUSER_PASSWORD,
    }
    with patch("app.services.jobs.start_scheduler"), \
         patch.dict(os.environ, env_overrides):
        application = create_app("testing")
    with application.app_context():
        yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def superuser_client(client):
    client.post("/login", data={
        "email": SUPERUSER_EMAIL,
        "password": SUPERUSER_PASSWORD,
    })
    return client


@pytest.fixture
def teacher(app):
    """The seeded superuser, used as the teacher in tests."""
    return User.query.filter_by(email=SUPERUSER_EMAIL).first()


@pytest.fixture
def open_slot(app, teacher):
    """An open lesson slot scheduled 14 days out."""
    slot = LessonSlot(
        teacher_id=teacher.id,
        title="Test Lesson",
        location="Studio A",
        scheduled_at=datetime.now() + timedelta(days=14),
        duration_minutes=60,
        min_threshold=3,
        max_capacity=5,
        status="open",
    )
    _db.session.add(slot)
    _db.session.commit()
    return slot
