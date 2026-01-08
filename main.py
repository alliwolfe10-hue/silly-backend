from fastapi import FastAPI
from fastapi.responses import Response
from datetime import date, timedelta
import uuid

app = FastAPI()

# Temporary in-memory storage
CALENDARS = {}

@app.post("/api/syllabi/analyze")
async def analyze():
    calendar_id = f"cal_{uuid.uuid4().hex[:8]}"

    CALENDARS[calendar_id] = {
        "name": "Silly – My Semester",
        "events": [
            {
                "uid": "exam1",
                "title": "Exam One — BBE 3013",
                "date": date(2025, 10, 6),
                "description": "Mon 10/6/2025 Exam One"
            },
            {
                "uid": "exam2",
                "title": "Exam Two — BBE 3013",
                "date": date(2025, 11, 10),
                "description": "Mon 11/10/2025 Exam Two"
            },
            {
                "uid": "final",
                "title": "Final Exam — BBE 3013",
                "date": date(2025, 12, 16),
                "description": "Tues 12/16/2025 Final Exam"
            }
        ]
    }

    return {
        "calendar_id": calendar_id,
        "ics_url": f"/api/calendar/{calendar_id}.ics"
    }

@app.get("/api/calendar/{calendar_id}.ics")
def get_calendar(calendar_id: str):
    cal = CALENDARS.get(calendar_id)
    if not cal:
        return Response("Not found", status_code=404)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Silly//Academic Calendar//EN",
        f"X-WR-CALNAME:{cal['name']}"
    ]

    for e in cal["events"]:
        start = e["date"]
        end = start + timedelta(days=1)
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{e['uid']}@silly.app",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
            f"SUMMARY:{e['title']}",
            f"DESCRIPTION:{e['description']}",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")

    return Response("\r\n".join(lines), media_type="text/calendar")
