from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from datetime import timedelta
from typing import List
import uuid

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


BASE_URL = "https://silly-backend.onrender.com"

# Temporary in-memory storage
CALENDARS = {}

@app.post("/api/syllabi/analyze")
async def analyze(files: List[UploadFile] = File(...)):
    _ = [f.filename for f in files]

    calendar_id = f"cal_{uuid.uuid4().hex[:8]}"

    CALENDARS[calendar_id] = {
        "name": "Silly – My Semester",
        "events": []
    }

    return {
        "calendar_id": calendar_id,
        "ics_url": f"{BASE_URL}/api/calendar/{calendar_id}.ics"
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
        f"X-WR-CALNAME:{cal['name']}",
        "END:VCALENDAR"
    ]

    return Response("\r\n".join(lines), media_type="text/calendar")
