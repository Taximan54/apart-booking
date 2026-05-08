import json
import uuid
import requests

from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# =========================
# CONFIG
# =========================

BOT_TOKEN = "8770383990:AAGzExWz3WYCNYcEaV39lzrIx2SGQFyOqlA"
ADMIN_ID = 1008661058

PRICE_PER_NIGHT = 70

FILE = "bookings.json"

# =========================
# APP
# =========================

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# =========================
# MODELS
# =========================

class Booking(BaseModel):
    checkin: str
    checkout: str

# =========================
# HELPERS
# =========================

def load_bookings():

    try:
        with open(FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    except:
        return []

def save_bookings(data):

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def send_telegram(text):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id": ADMIN_ID,
        "text": text
    })

def dates_conflict(checkin, checkout):

    bookings = load_bookings()

    for booking in bookings:

        existing_start = datetime.strptime(
            booking["checkin"],
            "%Y-%m-%d"
        ).date()

        existing_end = datetime.strptime(
            booking["checkout"],
            "%Y-%m-%d"
        ).date()

        if checkin < existing_end and checkout > existing_start:
            return True

    return False

# =========================
# ROUTES
# =========================

@app.get("/")
async def home():

    return FileResponse("static/index.html")

@app.get("/busy-dates")
async def busy_dates():

    return load_bookings()

@app.post("/book")
async def book(data: Booking):

    checkin = datetime.strptime(
        data.checkin,
        "%Y-%m-%d"
    ).date()

    checkout = datetime.strptime(
        data.checkout,
        "%Y-%m-%d"
    ).date()

    # Проверка дат

    if checkout <= checkin:

        return JSONResponse({
            "success": False,
            "message": "Неверный диапазон дат"
        })

    # Проверка конфликта

    if dates_conflict(checkin, checkout):

        return JSONResponse({
            "success": False,
            "message": "Даты уже заняты"
        })

    nights = (checkout - checkin).days

    total = nights * PRICE_PER_NIGHT

    booking_id = str(uuid.uuid4())[:8]

    bookings = load_bookings()

    bookings.append({
        "id": booking_id,
        "checkin": str(checkin),
        "checkout": str(checkout),
        "nights": nights,
        "total": total
    })

    save_bookings(bookings)

    # Telegram уведомление

    send_telegram(
        f"🔥 НОВАЯ БРОНЬ\n\n"
        f"ID: {booking_id}\n"
        f"Заезд: {checkin}\n"
        f"Выезд: {checkout}\n"
        f"Ночей: {nights}\n"
        f"Сумма: {total}€"
    )

    return {
        "success": True,
        "booking_id": booking_id,
        "nights": nights,
        "total": total
    }