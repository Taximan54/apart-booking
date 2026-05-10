import os
import asyncio
import sqlite3
import uuid

from datetime import datetime, date

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    FSInputFile,
    InputMediaPhoto
)

# ==================================================
# CONFIG
# ==================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

ADMIN_IDS = [
    1008661058,
    1220835758
]

PRICE_PER_NIGHT = 70

DB_NAME = "bookings.db"

SITE_URL = "https://apart-booking-production.up.railway.app"

PHOTOS = [
    "static/images/1.JPG",
    "static/images/2.JPG",
    "static/images/3.JPG"
]

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

    today = date.today()

    checkin = datetime.strptime(
        data.checkin,
        "%Y-%m-%d"
    ).date()

    checkout = datetime.strptime(
        data.checkout,
        "%Y-%m-%d"
    ).date()

    if checkin > checkout:

        checkin, checkout = checkout, checkin

    if checkin < today:

        return JSONResponse({
            "success": False,
            "message": "Нельзя бронировать прошедшие даты"
        })

    if checkout <= today:

        return JSONResponse({
            "success": False,
            "message": "Некорректная дата выезда"
        })

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
            print(e)

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
# PHOTOS
# ==================================================

async def send_photos(message):

    media = []

    for i, photo in enumerate(PHOTOS):

        if i == 0:

            media.append(
                InputMediaPhoto(
                    media=FSInputFile(photo),
                    caption="🏠 ONE APART"
                )
            )

        else:

            media.append(
                InputMediaPhoto(
                    media=FSInputFile(photo)
                )
            )

    await message.answer_media_group(media)

# ==================================================
# START
# ==================================================

@dp.message(Command("start"))
async def start(message: Message):

    kb = ReplyKeyboardMarkup(
        keyboard=[

            [
                KeyboardButton(
                    text="📅 Забронировать",
                    web_app=WebAppInfo(
                        url=SITE_URL
                    )
                )
            ],

            [
                KeyboardButton(
                    text="📸 Фото квартиры"
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
        "🏠 ONE APART\nДобро пожаловать",
        reply_markup=kb
    )

# ==================================================
# ADMIN
# ==================================================

@dp.message(Command("admin"))
async def admin(message: Message):

    if not is_admin(message.from_user.id):

        await message.answer(
            "Нет доступа"
        )

        return

    await message.answer(
        "🏠 ONE APART ADMIN",
        reply_markup=admin_keyboard()
    )

# ==================================================
# PHOTOS BUTTON
# ==================================================

@dp.message(F.text == "📸 Фото квартиры")
async def photos(message: Message):

    await send_photos(message)

# ==================================================
# DESCRIPTION
# ==================================================

@dp.message(F.text == "📋 Описание квартиры")
async def description(message: Message):

    text = """
С НАМИ КОМФОРТНО❣️
Добро пожаловать 🤗  в квартиру комфорт класса❗️
Абсолютная чистота - контроль качества уборки квартиры.🪷
Светлая, просторная, квартира с новым качественным ремонтом, рядом с центром Новосибирска на площади Калинина.
Высокий этаж, панорамное остекление, шикарный вид из окна.
Если вы гость в Новосибирске, находитесь в командировке или хотите отвлечься от рутины, сменить обстановку, наша студия - идеальный выбор!

В квартире может проживать не более 2 гостей❗️
Условия для размещения с детьми не предусмотрены❗️

ДЛЯ ВАС:
🔆в комнате: двухспальная кровать шириной 160 см с ортопедическим матрасом, подушки 4 шт., высококачественное постельное белье 100% хлопок, любителям поспать для комфортного сна шторы блэкаут, разные варианты освещения, кондиционер-инвертор, смарт-телевизор, туалетный столик, вместительный комод, прикроватные тумбы, комфортный диван (не раскладной), Wi-Fi 🛜

🔆в ванной комната: свежие махровые полотенца, ванные принадлежности: гель для душа, шампунь, кондиционер для волос, жидкое мыло для рук, крем для рук, предметы гигиены, одноразовая паста и зубная щётка, душевая колонна, ванна, водонагреватель, фен

🔆на кухне: шикарный кухонный гарнитур с барной стойкой, барные стулья, микроволновая печь, духовка, индукционная варочная плита, холодильник, чайник, посуда, рабочее место

🔆в прихожей: большой шкаф, стиральная машина с сушкой, утюг, гладильная доска, сушилка, зонтик ☂️

🎁 Гостям предоставлены: кофе ☕️, черный чай, сахар

Удобное месторасположение дома‼️

В ШАГОВОЙ ДОСТУПНОСТИ:
▪️Ⓜ️ Заельцовская
▪️Ⓜ️ Гагаринская
▪️Зоопарк
▪️Дендропарк
▪️ТЦ Роял Парк
▪️рестораны
▪️аптеки
▪️банки
▪️фитнес клубы

БЕЗ ПЕРЕСАДОК ДОЕДИТЕ ДО:
📍 Центр города
📍 Аквапарк Аквамир
📍 НОВАТ
📍 Термы Мира
📍 Сибирь-Арена
📍 Михайловская набережная

Внимание ⚠️
Цена зависит от дней проживания, будни/выходные/праздничные дни.

Заезд в 15:00
Выезд в 12:00

ДЕПОЗИТ 6000 руб.

⛔️ ЗАПРЕЩЕНО:
КУРИТЬ
ПРОВОДИТЬ ВЕЧЕРИНКИ
"""

    await message.answer(text)

# ==================================================
# CONTACT
# ==================================================

@dp.message(F.text == "📞 Связаться")
async def contact(message: Message):

    await message.answer(
        "Напишите администратору."
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

    if not is_admin(callback.from_user.id):

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

    if not is_admin(callback.from_user.id):

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