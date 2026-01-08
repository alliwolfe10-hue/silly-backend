from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from datetime import date, timedelta
from typing import List
import uuid


app = FastAPI()

# Temporary in-memory storage
CALENDARS = {}

@app.post("/api/syllabi/analyze")
async def analyze(files: List[UploadFile] = File(...)):
    _ = [f.filename for f in files]

    calendar_id = f"cal_{uuid.uuid4().hex[:8]}"

    # For now, ignore file contents — just accept them
    CALENDARS[calendar_id] = {
        "name": "Silly – My Semester",
        "events": []
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
# deploy trigger

