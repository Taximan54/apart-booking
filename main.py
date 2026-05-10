import os
import asyncio
import sqlite3
import uuid

from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import (
    FileResponse,
    JSONResponse
)
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

# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = os.getenv("8770383990:AAE3mqsQtIxbPE5YrntEz-Y4Jfc-93ezuGc")

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

def get_connection():

    conn = sqlite3.connect(
        DB_NAME,
        check_same_thread=False
    )

    conn.row_factory = sqlite3.Row

    return conn

def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (

        id TEXT PRIMARY KEY,

        checkin TEXT NOT NULL,

        checkout TEXT NOT NULL,

        nights INTEGER NOT NULL,

        total INTEGER NOT NULL,

        created_at TEXT NOT NULL
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

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM bookings
    ORDER BY checkin ASC
    """)

    rows = cursor.fetchall()

    conn.close()

    bookings = []

    for row in rows:

        bookings.append({
            "id": row["id"],
            "checkin": row["checkin"],
            "checkout": row["checkout"],
            "nights": row["nights"],
            "total": row["total"],
            "created_at": row["created_at"]
        })

    return bookings

def has_conflict(checkin, checkout):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM bookings
    WHERE (
        checkin < ?
        AND checkout > ?
    )
    """, (
        str(checkout),
        str(checkin)
    ))

    count = cursor.fetchone()[0]

    conn.close()

    return count > 0

def create_booking(checkin, checkout):

    conn = get_connection()

    cursor = conn.cursor()

    try:

        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute("""
        SELECT COUNT(*)
        FROM bookings
        WHERE (
            checkin < ?
            AND checkout > ?
        )
        """, (
            str(checkout),
            str(checkin)
        ))

        count = cursor.fetchone()[0]

        if count > 0:

            conn.rollback()

            return None

        nights = (
            checkout - checkin
        ).days

        total = nights * PRICE_PER_NIGHT

        booking_id = str(
            uuid.uuid4()
        )[:8]

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

        return {
            "id": booking_id,
            "nights": nights,
            "total": total
        }

    except Exception as e:

        conn.rollback()

        print("BOOKING ERROR:", e)

        return None

    finally:

        conn.close()

def delete_booking(booking_id):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM bookings
    WHERE id = ?
    """, (booking_id,))

    conn.commit()

    deleted = cursor.rowcount

    conn.close()

    return deleted > 0

def stats():

    bookings = get_bookings()

    revenue = sum(
        booking["total"]
        for booking in bookings
    )

    nights = sum(
        booking["nights"]
        for booking in bookings
    )

    return {
        "bookings": len(bookings),
        "revenue": revenue,
        "nights": nights
    }

# ==================================================
# MODELS
# ==================================================

class BookingRequest(BaseModel):

    checkin: str
    checkout: str

# ==================================================
# WEB ROUTES
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

    try:

        checkin = datetime.strptime(
            data.checkin,
            "%Y-%m-%d"
        ).date()

        checkout = datetime.strptime(
            data.checkout,
            "%Y-%m-%d"
        ).date()

    except:

        return JSONResponse({
            "success": False,
            "message": "Ошибка даты"
        })

    if checkin >= checkout:

        return JSONResponse({
            "success": False,
            "message": "Минимум 1 ночь"
        })

    booking = create_booking(
        checkin,
        checkout
    )

    if not booking:

        return JSONResponse({
            "success": False,
            "message": "Даты уже заняты"
        })

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

        except Exception as e:

            print(
                "TELEGRAM ERROR:",
                e
            )

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

# ==================================================
# TELEGRAM START
# ==================================================

@dp.message(Command("start"))
async def start(message: Message):

    if not is_admin(
        message.from_user.id
    ):

        await message.answer(
            "У вас нет доступа"
        )

        return

    await message.answer(
        text="🏠 ONE APART ADMIN",
        reply_markup=admin_keyboard()
    )

# ==================================================
# BOOKINGS
# ==================================================

@dp.callback_query(
    lambda c: c.data == "bookings"
)
async def bookings_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

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

        await callback.answer()

        return

    for booking in bookings:

        await callback.message.answer(

            f"🏠 Бронь #{booking['id']}\n\n"

            f"📅 {booking['checkin']} → "
            f"{booking['checkout']}\n"

            f"🌙 {booking['nights']} ночей\n"

            f"💰 {booking['total']}€",

            reply_markup=booking_keyboard(
                booking["id"]
            )
        )

    await callback.answer()

# ==================================================
# STATS
# ==================================================

@dp.callback_query(
    lambda c: c.data == "stats"
)
async def stats_callback(
    callback: CallbackQuery
):

    if not is_admin(
        callback.from_user.id
    ):

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

        return

    s = stats()

    await callback.message.answer(

        f"📊 СТАТИСТИКА\n\n"

        f"📅 Броней: {s['bookings']}\n"

        f"🌙 Ночей: {s['nights']}\n"

        f"💰 Доход: {s['revenue']}€"
    )

    await callback.answer()

# ==================================================
# DELETE BOOKING
# ==================================================

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

        await callback.answer(
            "Нет доступа",
            show_alert=True
        )

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

    await callback.answer()

# ==================================================
# STARTUP
# ==================================================

@app.on_event("startup")
async def startup():

    asyncio.create_task(
        dp.start_polling(bot)
    )

# ==================================================
# MAIN
# ==================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            8000
        )
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False
    )