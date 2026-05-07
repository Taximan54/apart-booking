from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import json
import uuid
from datetime import datetime, timedelta

app = FastAPI()

# ---------------- CORS ----------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- STATIC ----------------

app.mount("/static", StaticFiles(directory="static"), name="static")

# ---------------- FILE ----------------

FILE = "bookings.json"

# ---------------- HELPERS ----------------

def load_bookings():
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_bookings(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ---------------- MODEL ----------------

class Booking(BaseModel):
    checkin: str
    checkout: str

# ---------------- INDEX ----------------

@app.get("/")
async def index():
    return FileResponse("static/index.html")

# ---------------- BUSY DATES ----------------

@app.get("/busy-dates")
async def busy_dates():

    bookings = load_bookings()

    busy = []

    for b in bookings:

        start = datetime.strptime(b["checkin"], "%Y-%m-%d").date()
        end = datetime.strptime(b["checkout"], "%Y-%m-%d").date()

        current = start

        while current < end:

            busy.append(current.strftime("%Y-%m-%d"))

            current += timedelta(days=1)

    return busy

# ---------------- BOOK ----------------

@app.post("/book")
async def book(data: Booking):

    bookings = load_bookings()

    booking = {
        "id": str(uuid.uuid4())[:8],
        "checkin": data.checkin,
        "checkout": data.checkout
    }

    bookings.append(booking)

    save_bookings(bookings)

    return {
        "success": True,
        "booking_id": booking["id"]
    }