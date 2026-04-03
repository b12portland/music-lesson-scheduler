from datetime import timezone
from icalendar import Calendar, Event
import uuid


def generate_ics(slot, booking):
    cal = Calendar()
    cal.add("prodid", "-//Music Lessons Scheduler//EN")
    cal.add("version", "2.0")
    cal.add("method", "REQUEST")

    event = Event()
    event.add("summary", slot.title)
    event.add("dtstart", slot.scheduled_at.replace(tzinfo=timezone.utc))

    from datetime import timedelta
    end_time = slot.scheduled_at + timedelta(minutes=slot.duration_minutes)
    event.add("dtend", end_time.replace(tzinfo=timezone.utc))
    event.add("location", slot.location)
    event.add("description", slot.description or "")
    event.add("uid", str(uuid.uuid4()))

    cal.add_component(event)
    return cal.to_ical()
