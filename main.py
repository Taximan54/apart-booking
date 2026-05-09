import asyncio
import sqlite3
import uuid

from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

# =====================================================
# CONFIG
# =====================================================

BOT_TOKEN = "8770383990:AAGzExWz3WYCNYcEaV39lzrIx2SGQFyOqlA"

ADMIN_IDS = [
    1008661058,
    1220835758
]

PRICE_PER_NIGHT = 70

DB_NAME = "bookings.db"

# =====================================================
# FASTAPI
# =====================================================

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# =====================================================
# TELEGRAM
# =====================================================

bot = Bot(token=BOT_TOKEN)

dp = Dispatcher()

# =====================================================
# DATABASE
# =====================================================

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

# =====================================================
# HELPERS
# =====================================================

def is_admin(user_id):

    return user_id in ADMIN_IDS

def get_all_bookings():

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

def revenue_stats():

    bookings = get_all_bookings()

    total_revenue = sum(
        booking["total"]
        for booking in bookings
    )

    total_nights = sum(
        booking["nights"]
        for booking in bookings
    )

    total_bookings = len(bookings)

    return {
        "revenue": total_revenue,
        "nights": total_nights,
        "bookings": total_bookings
    }

async def notify_admins(text):

    for admin_id in ADMIN_IDS:

        try:

            await bot.send_message(
                admin_id,
                text
            )

        except:
            pass

# =====================================================
# MODELS
# =====================================================

class BookingRequest(BaseModel):

    checkin: str
    checkout: str

# =====================================================
# WEB ROUTES
# =====================================================

@app.get("/")
async def home():

    return FileResponse(
        "static/index.html"
    )

@app.get("/busy-dates")
async def busy_dates():

    return get_all_bookings()

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

    # reverse selection fix
    if checkin > checkout:

        checkin, checkout = checkout, checkin

    if checkin == checkout:

        return JSONResponse({
            "success": False,
            "message": "Минимум 1 ночь"
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

    await notify_admins(
        f"🔥 НОВАЯ БРОНЬ\n\n"
        f"ID: {booking['id']}\n"
        f"📅 {checkin} → {checkout}\n"
        f"🌙 {booking['nights']} ночей\n"
        f"💰 {booking['total']}€"
    )

    return {
        "success": True,
        "booking_id": booking["id"],
        "nights": booking["nights"],
        "total": booking["total"]
    }

# =====================================================
# TELEGRAM CRM UI
# =====================================================

def admin_menu():

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
            ],

            [
                InlineKeyboardButton(
                    text="🔄 Обновить",
                    callback_data="refresh"
                )
            ]
        ]
    )

def booking_keyboard(booking_id):

    return InlineKeyboardMarkup(
        inline_keyboard=[

            [
                InlineKeyboardButton(
                    text="❌ Удалить",
                    callback_data=f"delete_{booking_id}"
                )
            ]
        ]
    )

# =====================================================
# START
# =====================================================

@dp.message(Command("start"))
async def start(message: Message):

    if not is_admin(
        message.from_user.id
    ):
        return

    await message.answer(
        "🏠 ONE APART ADMIN",
        reply_markup=admin_menu()
    )

# =====================================================
# BOOKINGS
# =====================================================

@dp.callback_query(
    lambda c: c.data == "bookings"
)
async def bookings_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    bookings = get_all_bookings()

    if not bookings:

        await callback.message.answer(
            "Броней нет"
        )

        return

    for booking in bookings:

        text = (
            f"🏠 Бронь #{booking['id']}\n\n"
            f"📅 {booking['checkin']} → "
            f"{booking['checkout']}\n"
            f"🌙 {booking['nights']} ночей\n"
            f"💰 {booking['total']}€"
        )

        await callback.message.answer(
            text,
            reply_markup=booking_keyboard(
                booking["id"]
            )
        )

# =====================================================
# STATS
# =====================================================

@dp.callback_query(
    lambda c: c.data == "stats"
)
async def stats_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    stats = revenue_stats()

    await callback.message.answer(
        f"📊 СТАТИСТИКА\n\n"
        f"📅 Броней: {stats['bookings']}\n"
        f"🌙 Ночей: {stats['nights']}\n"
        f"💰 Доход: {stats['revenue']}€"
    )

# =====================================================
# DELETE BOOKING
# =====================================================

@dp.callback_query(
    lambda c: c.data.startswith(
        "delete_"
    )
)
async def delete_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    booking_id = callback.data.replace(
        "delete_",
        ""
    )

    success = delete_booking(
        booking_id
    )

    if success:

        await callback.message.edit_text(
            f"❌ Бронь {booking_id} удалена"
        )

    else:

        await callback.message.answer(
            "Ошибка удаления"
        )

# =====================================================
# REFRESH
# =====================================================

@dp.callback_query(
    lambda c: c.data == "refresh"
)
async def refresh_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):
        return

    await callback.message.answer(
        "✅ Данные обновлены",
        reply_markup=admin_menu()
    )

# =====================================================
# BOT STARTUP
# =====================================================

async def start_bot():

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(bot)

# =====================================================
# FASTAPI STARTUP
# =====================================================

@app.on_event("startup")
async def startup_event():

    loop = asyncio.get_event_loop()

    loop.create_task(
        start_bot()
    )