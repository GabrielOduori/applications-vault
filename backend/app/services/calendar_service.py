from datetime import datetime, timedelta
from icalendar import Calendar, Event, Alarm


def generate_job_ics(title: str, organisation: str | None, url: str | None,
                     notes: str | None, deadline_date: str) -> bytes:
    cal = Calendar()
    cal.add("prodid", "-//ApplicationVault//EN")
    cal.add("version", "2.0")

    event = Event()
    summary = f"Deadline: {title}"
    if organisation:
        summary += f" at {organisation}"
    event.add("summary", summary)

    dt = datetime.strptime(deadline_date, "%Y-%m-%d")
    event.add("dtstart", dt.date())
    event.add("dtend", dt.date())

    description_parts = []
    if url:
        description_parts.append(f"Job URL: {url}")
    if notes:
        description_parts.append(f"Notes: {notes}")
    if description_parts:
        event.add("description", "\n".join(description_parts))

    # Reminders: 7 days, 2 days, morning of
    for delta in [timedelta(days=7), timedelta(days=2), timedelta(hours=0)]:
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add("trigger", -delta)
        alarm.add("description", f"Deadline reminder: {title}")
        event.add_component(alarm)

    cal.add_component(event)
    return cal.to_ical()
