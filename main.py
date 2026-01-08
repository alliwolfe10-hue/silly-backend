from fastapi import FastAPI, UploadFile, File
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from datetime import date, timedelta
import uuid
import re
from pypdf import PdfReader
from io import BytesIO

app = FastAPI()

# --------------------------------------------------
# CORS
# --------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------
# In-memory storage (temporary)
# --------------------------------------------------
CALENDARS = {}

# --------------------------------------------------
# Regex
# --------------------------------------------------

# MM/DD/YYYY
DATE_WITH_YEAR_REGEX = re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")

# MM/DD (no year)
DATE_NO_YEAR_REGEX = re.compile(r"\b(\d{1,2})/(\d{1,2})\b")

# Deliverable keywords (hard gate)
DELIVERABLE_REGEX = re.compile(
    r"\b(exam|midterm|final|quiz|due|deadline)\b",
    re.IGNORECASE
)

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def infer_year(month: int) -> int:
    """
    Conservative UMN-style academic year inference.
    Aug–Dec  -> 2025
    Jan–May  -> 2026
    """
    return 2025 if month >= 8 else 2026


def extract_event_date(line: str) -> date | None:
    """
    Extract date from a line.
    Supports MM/DD/YYYY and MM/DD with safe year inference.
    """
    match_with_year = DATE_WITH_YEAR_REGEX.search(line)
    if match_with_year:
        month, day, year = map(int, match_with_year.groups())
    else:
        match_no_year = DATE_NO_YEAR_REGEX.search(line)
        if not match_no_year:
            return None
        month, day = map(int, match_no_year.groups())
        year = infer_year(month)

    try:
        return date(year, month, day)
    except ValueError:
        return None


def reconstruct_logical_line(lines: List[str], start_idx: int, max_lookahead: int = 5) -> tuple[str, int]:
    """
    Reconstruct a logical line by combining the current line with up to max_lookahead
    subsequent lines, stopping when we hit a deliverable keyword or another date.
    
    Returns: (combined_text, number_of_lines_consumed)
    """
    combined = lines[start_idx]
    lines_consumed = 1
    
    for offset in range(1, min(max_lookahead + 1, len(lines) - start_idx)):
        next_line = lines[start_idx + offset]
        
        # Stop if we hit another date (likely a new event)
        if extract_event_date(next_line):
            break
            
        # Add this line to our reconstruction
        combined += " " + next_line
        lines_consumed += 1
        
        # If we now have a deliverable keyword, we can stop
        if DELIVERABLE_REGEX.search(combined):
            break
    
    return combined, lines_consumed


# --------------------------------------------------
# API: Analyze syllabus
# --------------------------------------------------
@app.post("/api/syllabi/analyze")
async def analyze(files: List[UploadFile] = File(...)):
    calendar_id = f"cal_{uuid.uuid4().hex[:8]}"
    events = []
    event_counter = 1

    for file in files:
        pdf_bytes = await file.read()
        reader = PdfReader(BytesIO(pdf_bytes))

        for page_index, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
# DEBUG: Print first 50 lines of each page
if page_index <= 2:  # Only first 2 pages
    print(f"\n=== PAGE {page_index} ===")
    for idx, ln in enumerate(lines[:50]):
        print(f"{idx}: {ln}")
            i = 0
            while i < len(lines):
                line = lines[i]

                event_date = extract_event_date(line)
                if not event_date:
                    i += 1
                    continue

                # Reconstruct logical line to handle wrapping
                combined_line, consumed = reconstruct_logical_line(lines, i)
                
                # Only create event if we found a deliverable keyword
                if DELIVERABLE_REGEX.search(combined_line):
                    events.append({
                        "id": f"evt_{event_counter}",
                        "title": combined_line,
                        "date": event_date,
                        "source_line": combined_line,
                        "source_page": page_index,
                        "extraction_method": "regex"
                    })
                    event_counter += 1
                
                # Skip the lines we consumed
                i += consumed

    CALENDARS[calendar_id] = {
        "name": "Silly – My Semester",
        "events": events
    }

    return {
        "calendar_id": calendar_id,
        "events": [
            {
                "id": e["id"],
                "title": e["title"],
                "date": e["date"].isoformat(),
                "source_line": e["source_line"],
                "source_page": e["source_page"],
                "extraction_method": e["extraction_method"]
            }
            for e in events
        ],
        "ics_url": f"https://silly-backend.onrender.com/api/calendar/{calendar_id}.ics"
    }


# --------------------------------------------------
# API: ICS calendar
# --------------------------------------------------
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
            f"UID:{e['id']}@silly.app",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
            f"SUMMARY:{e['title']}",
            f"DESCRIPTION:Source (page {e['source_page']}): {e['source_line']}",
            "END:VEVENT"
        ])

    lines.append("END:VCALENDAR")
    return Response("\r\n".join(lines), media_type="text/calendar")