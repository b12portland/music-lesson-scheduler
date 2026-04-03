import logging
from datetime import timedelta
from app.utils import eastern_now
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler = None


def start_scheduler(app):
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        func=lambda: _run_hourly(app),
        trigger="interval",
        hours=1,
        start_date=eastern_now() + timedelta(minutes=1),
        id="hourly_job",
        replace_existing=True,
        coalesce=True,
        misfire_grace_time=300,
    )
    _scheduler.start()
    logger.info("Background scheduler started.")


def _run_hourly(app):
    with app.app_context():
        from app.services.scheduling import process_auto_closes, process_reminders
        from app.services.notifications import send_slot_closed, send_reminder_emails

        closed = process_auto_closes()
        for slot in closed:
            logger.info("Auto-closed slot: %s (id=%s)", slot.title, slot.id)
            send_slot_closed(slot)

        reminded = process_reminders()
        for slot in reminded:
            logger.info("Sent reminders for slot: %s (id=%s)", slot.title, slot.id)
