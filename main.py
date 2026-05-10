import os
import json
import uuid
import asyncio
import sqlite3

from datetime import datetime, date

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    WebAppInfo,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

ADMIN_IDS = [
    1008661058,
    1220835758
]

PRICE_PER_NIGHT = 70

DB_NAME = "bookings.db"

# ==================================================
# FASTAPI
# ==================================================

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# ==================================================
# TELEGRAM
# ==================================================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

# ==================================================
# DATABASE
# ==================================================

def init_db():

    conn = sqlite3.connect(DB_NAME)

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

# ==================================================
# HELPERS
# ==================================================

def is_admin(user_id):

    return int(user_id) in ADMIN_IDS

def get_bookings():

    conn = sqlite3.connect(DB_NAME)

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

def has_conflict(checkin, checkout):

    bookings = get_bookings()

    for booking in bookings:

        start = datetime.strptime(
            booking["checkin"],
            "%Y-%m-%d"
        ).date()

        end = datetime.strptime(
            booking["checkout"],
            "%Y-%m-%d"
        ).date()

        if checkin < end and checkout > start:
            return True

    return False

def create_booking(checkin, checkout):

    nights = (checkout - checkin).days

    total = nights * PRICE_PER_NIGHT

    booking_id = str(uuid.uuid4())[:8]

    conn = sqlite3.connect(DB_NAME)

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

    conn = sqlite3.connect(DB_NAME)

    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM bookings
    WHERE id = ?
    """, (booking_id,))

    conn.commit()

    deleted = cursor.rowcount

    conn.close()

    return deleted > 0

# ==================================================
# MODELS
# ==================================================

class BookingRequest(BaseModel):

    checkin: str
    checkout: str

# ==================================================
# WEB
# ==================================================

@app.get("/")
async def home():

    return FileResponse(
        "static/index.html"
    )

@app.get("/busy-dates")
async def busy_dates():

    return get_bookings()

@app.post("/book")
async def book(data: BookingRequest):

    today = date.today()

    checkin = datetime.strptime(
        data.checkin,
        "%Y-%m-%d"
    ).date()

    checkout = datetime.strptime(
        data.checkout,
        "%Y-%m-%d"
    ).date()

    if checkin >= checkout:

        return JSONResponse({
            "success": False,
            "message": "Минимум 1 ночь"
        })

    if checkin < today:

        return JSONResponse({
            "success": False,
            "message": "Нельзя бронировать прошедшие даты"
        })

    if has_conflict(checkin, checkout):

        return JSONResponse({
            "success": False,
            "message": "Даты заняты"
        })

    booking = create_booking(
        checkin,
        checkout
    )

    for admin_id in ADMIN_IDS:

        try:

            await bot.send_message(
                admin_id,
                f"🔥 НОВАЯ БРОНЬ\n\n"
                f"ID: {booking['id']}\n"
                f"📅 {checkin} → {checkout}\n"
                f"🌙 {booking['nights']} ночей\n"
                f"💰 {booking['total']}€"
            )

        except:
            pass

    return {
        "success": True,
        "booking_id": booking["id"],
        "nights": booking["nights"],
        "total": booking["total"]
    }

# ==================================================
# KEYBOARDS
# ==================================================

def admin_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="📅 Брони",
                    callback_data="bookings"
                )
            ],

            [
                InlineKeyboardButton(
                    text="💰 Статистика",
                    callback_data="stats"
                )
            ]
        ]
    )

# ==================================================
# TELEGRAM START
# ==================================================

@dp.message(CommandStart())
async def start(message: Message):

    kb = ReplyKeyboardMarkup(
        keyboard=[

            [
                KeyboardButton(
                    text="📅 Забронировать",
                    web_app=WebAppInfo(
                        url="https://apart-booking-production.up.railway.app"
                    )
                )
            ],

            [
                KeyboardButton(
                    text="📋 Описание квартиры"
                )
            ],

            [
                KeyboardButton(
                    text="📞 Связаться"
                )
            ]

        ],
        resize_keyboard=True
    )

    await message.answer(
        "Добро пожаловать 👋",
        reply_markup=kb
    )

    if is_admin(message.from_user.id):

        await message.answer(
            "🏠 ONE APART ADMIN",
            reply_markup=admin_keyboard()
        )

# ==================================================
# DESCRIPTION
# ==================================================

@dp.message(lambda m: m.text == "📋 Описание квартиры")
async def description(message: Message):

    text = open(
        "description.txt",
        "r",
        encoding="utf-8"
    ).read()

    await message.answer(text)

# ==================================================
# CONTACT
# ==================================================

@dp.message(lambda m: m.text == "📞 Связаться")
async def contact(message: Message):

    await message.answer(
        "Для бронирования и вопросов:\n@your_username"
    )

# ==================================================
# ADMIN BOOKINGS
# ==================================================

@dp.callback_query(lambda c: c.data == "bookings")
async def bookings_callback(callback):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    bookings = get_bookings()

    if not bookings:

        await callback.message.answer(
            "Броней пока нет"
        )

        return

    for booking in bookings:

        await callback.message.answer(

            f"🏠 Бронь #{booking['id']}\n\n"
            f"📅 {booking['checkin']} → "
            f"{booking['checkout']}\n"
            f"🌙 {booking['nights']} ночей\n"
            f"💰 {booking['total']}€"
        )

# ==================================================
# ADMIN STATS
# ==================================================

@dp.callback_query(lambda c: c.data == "stats")
async def stats_callback(callback):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    bookings = get_bookings()

    revenue = sum(
        booking["total"]
        for booking in bookings
    )

    nights = sum(
        booking["nights"]
        for booking in bookings
    )

    await callback.message.answer(

        f"📊 СТАТИСТИКА\n\n"
        f"📅 Броней: {len(bookings)}\n"
        f"🌙 Ночей: {nights}\n"
        f"💰 Доход: {revenue}€"
    )

# ==================================================
# STARTUP
# ==================================================

@app.on_event("startup")
async def startup():

    asyncio.create_task(
        dp.start_polling(bot)
    )