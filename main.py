import asyncio
import sqlite3
import uuid
import requests

from datetime import datetime
from threading import Thread

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# =========================================
# CONFIG
# =========================================

BOT_TOKEN = "8770383990:AAGzExWz3WYCNYcEaV39lzrIx2SGQFyOqlA"

ADMIN_IDS = [
    1008661058,
    1220835758
]

PRICE_PER_NIGHT = 70

DB = "bookings.db"

# =========================================
# FASTAPI
# =========================================

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# =========================================
# TELEGRAM
# =========================================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

# =========================================
# DATABASE
# =========================================

def init_db():

    conn = sqlite3.connect(DB)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id TEXT PRIMARY KEY,
        checkin TEXT,
        checkout TEXT,
        nights INTEGER,
        total INTEGER,
        created_at TEXT
    )
    """)

    conn.commit()

    conn.close()

init_db()

# =========================================
# HELPERS
# =========================================

def get_all_bookings():

    conn = sqlite3.connect(DB)

    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM bookings
    ORDER BY checkin ASC
    """)

    rows = cursor.fetchall()

    conn.close()

    bookings = []

    for row in rows:

        bookings.append({
            "id": row[0],
            "checkin": row[1],
            "checkout": row[2],
            "nights": row[3],
            "total": row[4],
            "created_at": row[5]
        })

    return bookings

def booking_conflict(checkin, checkout):

    bookings = get_all_bookings()

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

def create_booking(checkin, checkout):

    nights = (checkout - checkin).days

    total = nights * PRICE_PER_NIGHT

    booking_id = str(uuid.uuid4())[:8]

    conn = sqlite3.connect(DB)

    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO bookings
    VALUES (?, ?, ?, ?, ?, ?)
    """, (
        booking_id,
        str(checkin),
        str(checkout),
        nights,
        total,
        str(datetime.now())
    ))

    conn.commit()

    conn.close()

    return {
        "id": booking_id,
        "nights": nights,
        "total": total
    }

def delete_booking(booking_id):

    conn = sqlite3.connect(DB)

    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM bookings
    WHERE id = ?
    """, (booking_id,))

    conn.commit()

    deleted = cursor.rowcount

    conn.close()

    return deleted > 0

def revenue_stats():

    bookings = get_all_bookings()

    total_revenue = sum(b["total"] for b in bookings)

    total_nights = sum(b["nights"] for b in bookings)

    total_bookings = len(bookings)

    return {
        "revenue": total_revenue,
        "nights": total_nights,
        "bookings": total_bookings
    }

async def notify_admins(text):

    for admin_id in ADMIN_IDS:

        try:

            await bot.send_message(admin_id, text)

        except:
            pass

# =========================================
# MODELS
# =========================================

class BookingRequest(BaseModel):
    checkin: str
    checkout: str

# =========================================
# WEB ROUTES
# =========================================

@app.get("/")
async def home():

    return FileResponse("static/index.html")

@app.get("/busy-dates")
async def busy_dates():

    bookings = get_all_bookings()

    return bookings

@app.post("/book")
async def book(data: BookingRequest):

    checkin = datetime.strptime(
        data.checkin,
        "%Y-%m-%d"
    ).date()

    checkout = datetime.strptime(
        data.checkout,
        "%Y-%m-%d"
    ).date()

    if checkout <= checkin:

        return JSONResponse({
            "success": False,
            "message": "Неверные даты"
        })

    if booking_conflict(checkin, checkout):

        return JSONResponse({
            "success": False,
            "message": "Даты уже заняты"
        })

    booking = create_booking(checkin, checkout)

    await notify_admins(
        f"🔥 НОВАЯ БРОНЬ\n\n"
        f"ID: {booking['id']}\n"
        f"Заезд: {checkin}\n"
        f"Выезд: {checkout}\n"
        f"Ночей: {booking['nights']}\n"
        f"Сумма: {booking['total']}€"
    )

    return {
        "success": True,
        "booking_id": booking["id"],
        "nights": booking["nights"],
        "total": booking["total"]
    }

# =========================================
# TELEGRAM ADMIN PANEL
# =========================================

def is_admin(user_id):

    return user_id in ADMIN_IDS

@dp.message(Command("start"))
async def start(message: Message):

    if is_admin(message.from_user.id):

        await message.answer(
            "✅ ADMIN PANEL\n\n"
            "/bookings — все брони\n"
            "/stats — статистика\n"
            "/delete ID — удалить бронь"
        )

    else:

        await message.answer(
            "ONE APART 🏠"
        )

@dp.message(Command("bookings"))
async def bookings(message: Message):

    if not is_admin(message.from_user.id):
        return

    data = get_all_bookings()

    if not data:

        await message.answer("Броней нет")

        return

    text = "📅 ВСЕ БРОНИ\n\n"

    for b in data:

        text += (
            f"ID: {b['id']}\n"
            f"{b['checkin']} → {b['checkout']}\n"
            f"{b['nights']} ночей\n"
            f"{b['total']}€\n\n"
        )

    await message.answer(text)

@dp.message(Command("stats"))
async def stats(message: Message):

    if not is_admin(message.from_user.id):
        return

    stats_data = revenue_stats()

    await message.answer(
        f"📊 СТАТИСТИКА\n\n"
        f"Броней: {stats_data['bookings']}\n"
        f"Ночей: {stats_data['nights']}\n"
        f"Доход: {stats_data['revenue']}€"
    )

@dp.message(Command("delete"))
async def delete(message: Message):

    if not is_admin(message.from_user.id):
        return

    parts = message.text.split()

    if len(parts) != 2:

        await message.answer(
            "Использование:\n/delete ID"
        )

        return

    booking_id = parts[1]

    success = delete_booking(booking_id)

    if success:

        await message.answer(
            f"✅ Бронь {booking_id} удалена"
        )

    else:

        await message.answer(
            "❌ Бронь не найдена"
        )

# =========================================
# RUN BOT
# =========================================

async def start_bot():

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

def run_bot():

    asyncio.run(start_bot())

# =========================================
# STARTUP
# =========================================

@app.on_event("startup")
async def startup_event():

    loop = asyncio.get_event_loop()

    loop.create_task(start_bot())