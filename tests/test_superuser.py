from datetime import datetime, timedelta
from app import db
from app.models import LessonSlot, User


def test_update_settings_with_conflicting_open_slots(app, superuser_client):
    """
    Regression: saving global settings when open slots exist raised NameError
    ('timezone' not defined) followed by TypeError (naive/aware datetime comparison).
    The route should complete and redirect, not crash with a 500.
    """
    teacher = User.query.filter_by(role="superuser").first()
    slot = LessonSlot(
        teacher_id=teacher.id,
        title="Test Lesson",
        location="Studio A",
        scheduled_at=datetime.now() + timedelta(days=5),
        duration_minutes=60,
        min_threshold=2,
        max_capacity=5,
        status="open",
    )
    db.session.add(slot)
    db.session.commit()

    # Increasing confirmation_required_before_days from 7 to 10 puts the
    # slot's new deadline (5 - 10 = -5 days) in the past, triggering the
    # conflict-detection branch that contained the bug.
    response = superuser_client.post("/admin/settings", data={
        "confirmation_required_before_days": "10",
        "reminder_days_before": "1",
    })

    assert response.status_code == 302
