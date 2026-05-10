import os
import json
import uuid
import asyncio
from datetime import datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    FSInputFile,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery
)

# =====================================================
# НАСТРОЙКИ
# =====================================================

BOT_TOKEN = os.environ["BOT_TOKEN"]

ADMIN_IDS = [
    1008661058
]

PRICE_PER_NIGHT = 70

BOOKINGS_FILE = "bookings.json"

BOOKING_STATUSES = {
    "pending": "⏳ Ожидание",
    "confirmed": "✅ Подтверждено",
    "cancelled": "❌ Отменено"
}

PHOTOS = [
    "static/images/1.JPG",
    "static/images/2.JPG",
    "static/images/3.JPG"
]

WEBAPP_URL = "https://apart-booking-production.up.railway.app"

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
# МОДЕЛЬ
# =====================================================

class Booking(BaseModel):
    checkin: str
    checkout: str

# =====================================================
# ФАЙЛ БРОНЕЙ
# =====================================================

def load_bookings():

    try:

        with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:

            return json.load(f)

    except:

        return []

def save_bookings(data):

    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )

# =====================================================
# HTML
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    html = f"""
<!DOCTYPE html>
<html lang="ru">
<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>ONE APART</title>

<style>

body{{
margin:0;
background:#f3f3f3;
font-family:Arial;
color:#111;
}}

.header{{
background:white;
padding:24px;
box-shadow:0 2px 10px rgba(0,0,0,0.05);
}}

.logo{{
font-size:34px;
font-weight:bold;
}}

.sub{{
margin-top:5px;
color:#666;
}}

.container{{
max-width:600px;
margin:auto;
padding:20px;
}}

.gallery{{
display:flex;
gap:14px;
overflow-x:auto;
margin-bottom:20px;
}}

.gallery img{{
width:100%;
max-width:520px;
height:320px;
object-fit:cover;
border-radius:24px;
flex-shrink:0;
}}

.card{{
background:white;
padding:24px;
border-radius:30px;
box-shadow:0 4px 20px rgba(0,0,0,0.05);
}}

.calendar-header{{
display:flex;
justify-content:space-between;
align-items:center;
margin-bottom:20px;
}}

.month{{
font-size:30px;
font-weight:bold;
}}

.nav{{
width:50px;
height:50px;
border:none;
border-radius:50%;
background:#f0f0f0;
font-size:24px;
cursor:pointer;
}}

.weekdays{{
display:grid;
grid-template-columns:repeat(7,1fr);
gap:10px;
margin-bottom:10px;
text-align:center;
color:#777;
}}

.calendar{{
display:grid;
grid-template-columns:repeat(7,1fr);
gap:10px;
}}

.day{{
aspect-ratio:1;
border-radius:18px;
display:flex;
align-items:center;
justify-content:center;
font-weight:bold;
cursor:pointer;
border:2px solid #eee;
background:white;
transition:0.2s;
}}

.day:hover{{
transform:scale(1.05);
}}

.busy{{
background:#ff6b6b;
color:white;
border:none;
cursor:not-allowed;
}}

.selected{{
background:black;
color:white;
border:none;
}}

.range{{
background:#ddd;
}}

.past{{
opacity:0.35;
cursor:not-allowed;
}}

.info{{
margin-top:25px;
text-align:center;
line-height:1.7;
font-size:18px;
}}

.price{{
font-size:42px;
font-weight:bold;
margin-top:16px;
}}

.btn{{
width:100%;
margin-top:30px;
padding:22px;
border:none;
border-radius:24px;
background:black;
color:white;
font-size:22px;
font-weight:bold;
cursor:pointer;
}}

.success{{
position:fixed;
inset:0;
background:rgba(0,0,0,0.7);
display:none;
justify-content:center;
align-items:center;
}}

.success-box{{
background:white;
padding:34px;
border-radius:28px;
width:90%;
max-width:420px;
text-align:center;
}}

.close{{
margin-top:20px;
padding:16px 30px;
border:none;
border-radius:18px;
background:black;
color:white;
font-size:18px;
}}

</style>

</head>

<body>

<div class="header">

<div class="logo">
ONE APART
</div>

<div class="sub">
Пауза в городе • Новосибирск
</div>

</div>

<div class="container">

<div class="gallery">

<img src="/static/images/1.JPG">
<img src="/static/images/2.JPG">
<img src="/static/images/3.JPG">

</div>

<div class="card">

<div class="calendar-header">

<button class="nav" onclick="prevMonth()">‹</button>

<div class="month" id="monthName"></div>

<button class="nav" onclick="nextMonth()">›</button>

</div>

<div class="weekdays">

<div>Пн</div>
<div>Вт</div>
<div>Ср</div>
<div>Чт</div>
<div>Пт</div>
<div>Сб</div>
<div>Вс</div>

</div>

<div class="calendar" id="calendar"></div>

<div class="info" id="info"></div>

<button class="btn" onclick="bookDate()">
Забронировать
</button>

</div>

</div>

<div class="success" id="success">

<div class="success-box">

<h2>Бронь создана</h2>

<div id="successText"></div>

<button class="close" onclick="closeSuccess()">
Закрыть
</button>

</div>

</div>

<script>

let busyDates = []

let checkin = null
let checkout = null

const PRICE = {PRICE_PER_NIGHT}

const today = new Date()
today.setHours(0,0,0,0)

let currentMonth = today.getMonth()
let currentYear = today.getFullYear()

const monthNames = [
"Январь",
"Февраль",
"Март",
"Апрель",
"Май",
"Июнь",
"Июль",
"Август",
"Сентябрь",
"Октябрь",
"Ноябрь",
"Декабрь"
]

async function loadBusyDates(){{

const response = await fetch("/busy-dates")

busyDates = await response.json()

renderCalendar()

}}

function isBusy(date){{

for(let b of busyDates){{

if(
date < b.checkout &&
date >= b.checkin &&
b.status !== "cancelled"
){{
return true
}}

}}

return false

}}

function renderCalendar(){{

const calendar = document.getElementById("calendar")

calendar.innerHTML = ""

document.getElementById("monthName").innerText =
`${{monthNames[currentMonth]}} ${{currentYear}}`

const daysInMonth =
new Date(currentYear,currentMonth+1,0).getDate()

for(let day=1; day<=daysInMonth; day++){{

const date =
`${{currentYear}}-${{String(currentMonth+1).padStart(2,'0')}}-${{String(day).padStart(2,'0')}}`

const div = document.createElement("div")

div.className = "day"

div.innerText = day

const dateObj = new Date(date)

if(dateObj < today){{

div.classList.add("past")

}}

else if(isBusy(date)){{

div.classList.add("busy")

}}

else{{

div.onclick = ()=>selectDate(date)

}}

if(checkin && date===checkin){{
div.classList.add("selected")
}}

if(checkout && date===checkout){{
div.classList.add("selected")
}}

if(checkin && checkout){{
if(date > checkin && date < checkout){{
div.classList.add("range")
}}
}}

calendar.appendChild(div)

}}

updateInfo()

}}

function selectDate(date){{

const selectedDate = new Date(date)

if(selectedDate < today){{
return
}}

if(!checkin){{

checkin = date
checkout = null

renderCalendar()

return

}}

if(!checkout){{

if(date <= checkin){{

checkin = date

renderCalendar()

return

}}

checkout = date

renderCalendar()

return

}}

checkin = date
checkout = null

renderCalendar()

}}

function updateInfo(){{

const info = document.getElementById("info")

if(checkin && !checkout){{

info.innerHTML =
`Заезд:<br><b>${{checkin}}</b>`

return

}}

if(checkin && checkout){{

const start = new Date(checkin)
const end = new Date(checkout)

const nights =
(end-start)/(1000*60*60*24)

const total =
nights * PRICE

info.innerHTML =
`
Заезд: <b>${{checkin}}</b><br>
Выезд: <b>${{checkout}}</b><br>
Ночей: <b>${{nights}}</b>

<div class="price">
${{total}}€
</div>
`

}}

}}

function prevMonth(){{

currentMonth--

if(currentMonth < 0){{
currentMonth = 11
currentYear--
}}

renderCalendar()

}}

function nextMonth(){{

currentMonth++

if(currentMonth > 11){{
currentMonth = 0
currentYear++
}}

renderCalendar()

}}

async function bookDate(){{

if(!checkin || !checkout){{
alert("Выберите даты")
return
}}

const response = await fetch("/book",{{

method:"POST",

headers:{{
"Content-Type":"application/json"
}},

body:JSON.stringify({{
checkin,
checkout
}})

}})

const data = await response.json()

if(data.success){{

document.getElementById("success").style.display =
"flex"

document.getElementById("successText").innerHTML =
`
ID: <b>${{data.booking_id}}</b><br><br>

${{checkin}} → ${{checkout}}<br>

${{data.nights}} ночей<br><br>

<b>${{data.total}}€</b>
`

loadBusyDates()

}}

else{{

alert(data.message)

}}

}}

function closeSuccess(){{
location.reload()
}}

loadBusyDates()

</script>

</body>
</html>
"""

    return HTMLResponse(html)

# =====================================================
# BUSY DATES
# =====================================================

@app.get("/busy-dates")
async def busy_dates():

    return JSONResponse(load_bookings())

# =====================================================
# BOOKING
# =====================================================

@app.post("/book")
async def book(data: Booking):

    bookings = load_bookings()

    today = datetime.now().date()

    checkin = datetime.strptime(
        data.checkin,
        "%Y-%m-%d"
    ).date()

    checkout = datetime.strptime(
        data.checkout,
        "%Y-%m-%d"
    ).date()

    if checkin < today:

        return {
            "success": False,
            "message": "Нельзя бронировать прошлые даты"
        }

    if checkout <= checkin:

        return {
            "success": False,
            "message": "Некорректные даты"
        }

    for b in bookings:

        if b["status"] == "cancelled":
            continue

        booked_checkin = datetime.strptime(
            b["checkin"],
            "%Y-%m-%d"
        ).date()

        booked_checkout = datetime.strptime(
            b["checkout"],
            "%Y-%m-%d"
        ).date()

        if (
            checkin < booked_checkout and
            checkout > booked_checkin
        ):

            return {
                "success": False,
                "message": "Даты заняты"
            }

    nights = (checkout - checkin).days

    total = nights * PRICE_PER_NIGHT

    booking_id = str(uuid.uuid4())[:8]

    booking = {
        "id": booking_id,
        "checkin": str(checkin),
        "checkout": str(checkout),
        "nights": nights,
        "total": total,
        "status": "pending"
    }

    bookings.append(booking)

    save_bookings(bookings)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"confirm_{booking_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отменить",
                    callback_data=f"cancel_{booking_id}"
                )
            ]
        ]
    )

    for admin in ADMIN_IDS:

        await bot.send_message(
            admin,
            f"""
🔥 НОВАЯ БРОНЬ

ID: {booking_id}

Заезд: {checkin}
Выезд: {checkout}

Ночей: {nights}

Сумма: {total}€

Статус:
⏳ Ожидание
""",
            reply_markup=keyboard
        )

    return {
        "success": True,
        "booking_id": booking_id,
        "nights": nights,
        "total": total
    }

# =====================================================
# TELEGRAM PHOTO
# =====================================================

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

# =====================================================
# START
# =====================================================

@dp.message(CommandStart())
async def start(message: types.Message):

    keyboard = ReplyKeyboardMarkup(

        keyboard=[

            [
                KeyboardButton(
                    text="📅 Забронировать",
                    web_app=WebAppInfo(
                        url=WEBAPP_URL
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
                    text="🛠 Админка"
                )
            ]

        ],

        resize_keyboard=True
    )

    await message.answer(
        "Добро пожаловать в ONE APART ✨",
        reply_markup=keyboard
    )

    await send_photos(message)

# =====================================================
# PHOTO
# =====================================================

@dp.message(lambda m: m.text == "📸 Фото квартиры")
async def photos(message: types.Message):

    await send_photos(message)

# =====================================================
# DESCRIPTION
# =====================================================

@dp.message(lambda m: m.text == "📋 Описание квартиры")
async def apartment_description(message: types.Message):

    text = """С НАМИ КОМФОРТНО❣️
Добро пожаловать 🤗  в квартиру комфорт класса❗️
Абсолютная чистота - контроль качества уборки квартиры.🪷
Светлая, просторная, квартира с новым качественным ремонтом,  рядом с центром Новосибирска на площади Калинина.
Высокий этаж, панорамное остекление, шикарный вид из окна.
Если вы гость в Новосибирске, находитесь в командировке или хотите отвлечься от рутины, сменить обстановку, наша студия - идеальный выбор!

В квартире может проживать не более 2 гостей❗️
Условия для размещения с детьми не предусмотрены❗️

ДЛЯ ВАС:
🔆в комнате: двухспальная кровать шириной 160 см с ортопедическим матрасом, подушки 4 шт., высококачественное постельное белье 100% хлопок, любителям поспать для комфортного сна шторы блэкаут, разные варианты освещения, кондиционер-инвертор, смарт-телевизор, туалетный столик, вместительный комод, прикроватные тумбы, комфортный диван (не раскладной), Wi-Fi 🛜 
🔆в ванной комната: свежие махровые полотенца, ванные принадлежности: гель для душа, шампунь, кондиционер для волос, жидкое мыло для рук, крем для рук, предметы гигиены, одноразовая паста и зубная щётка, душевая колонна, ванна, водонагреватель, фен
🔆на кухне: шикарный кухонный гарнитур с барной стойкой, барные стулья, микроволновая печь, духовка, индукционная варочная плита на 2 конфорки, 2-х камерный холодильник, чайник, столовые прибора, посуда сервировочная и для приготовления пищи, комфортное рабочее место за барной стойкой 
🔆в прихожей: большой вместительный шкаф, стиральная машина с функцией сушки, утюг, гладильная доска, раскладная сушилка для белья, пуфик, обувная  ложка, зонтик ☂️ 

🎁 Гостям предоставлены в зоне кухни: кофе☕️ черный чай, сахар

Удобное месторасположение дома‼️В ШАГОВОЙ ДОСТУПНОСТИ находятся:
станции метро 
▪️ Ⓜ️ Заельцовская 
▪️ Ⓜ️ Гагаринская
▪️Зоопарк 16 мин.пешком 
▪️Дендропарк Ботанический парк
▪️Парфюмерный магазин "Золотое Яблоко"
▪️остановки общественного транспорта 
▪️торговый центр "Роял Парк" с кинотеатром
▪️рестораны
▪️Лофт-парк "Подземка"
▪️аптеки, в том числе круглосуточные
▪️сетевые продуктовые, ювелирные и другие магазины
▪️продуктовый рынок "Заельцовский"
▪️банки и круглосуточные банкоматы
▪️салоны красоты и фитнес клубы

БЕЗ ПЕРЕСАДОК ДОЕДИТЕ ДО :
📍Центр города
📍Площадь и улица Ленина 
📍Зоопарк, Дельфинарий 
📍Цирк
📍"Гастрокорт" - гастрономическое пространство 
📍Аквапарк "Аквамир"
📍 Государственная Научно-Техническая Библиотека
📍 Михайловская набережная, расположенная вдоль побережья Оби
📍 Речной вокзал на Михайловской набережной для речных прогулок на теплоходе (сезонное)
📍 Колесо обозрения на Михайловской набережной 
📍 Собор Александра Невского
📍 Часовня Николая Чудотворца 
📍 Театр Оперы и Балета - НОВАТ
📍  Театр " Глобус "
📍 Драматический театр Сергея 
Афанасьева
📍Кукольный театр 🎭 
📍Краеведческий музей
📍Кинотеатр «Победа»
📍 Ледовая арена "Сибирь-Арена"
📍Термальный центр для восстановления и релакса "Термы Мира "
📍Горбольница
📍НИИТО
📍Центральный Парк: аттракционы, карусели 
📍Первомайский парк  
📍Заельцовсий Парк 

Добавьте наше объявление в избранное нажав на ❤️
Внимание ⚠️ ЦЕНА зависит от дней проживания, будни/выходные/праздничные дни.
Заезд в 15.00, выезд в 12.00 или в удобное для Вас время - по договоренности.
Ранний заезд/ поздний выезд только по предварительному согласованию при наличии возможности.

ДЕПОЗИТ 6000 руб. возвращается после выезда и уборки при соблюдении правил проживания.
Для заселения необходимо предъявить свои паспортные данные и внести полную оплату за проживание + депозит.
▪️Предоставляются ОТЧЁТНЫЕ ДОКУМЕНТЫ по требованию.
▪️Размещение без животных❗️

⛔️ ЗАПРЕЩЕНО: КУРИТЬ, ПРОВОДИТЬ ВЕЧЕРИНКИ ❗️
При нарушении - залог не возвращается❗️
"""

    await message.answer(text)

# =====================================================
# ADMIN PANEL
# =====================================================

@dp.message(lambda m: m.text == "🛠 Админка")
async def admin_panel(message: types.Message):

    if message.from_user.id not in ADMIN_IDS:

        return

    bookings = load_bookings()

    if not bookings:

        await message.answer("Броней пока нет")

        return

    text = "📋 ВСЕ БРОНИ\n\n"

    for b in bookings:

        text += f"""
ID: {b['id']}

{b['checkin']} → {b['checkout']}

{b['nights']} ночей

{b['total']}€

Статус:
{BOOKING_STATUSES.get(b['status'])}

-----------------------

"""

    await message.answer(text)

# =====================================================
# CONFIRM
# =====================================================

@dp.callback_query(lambda c: c.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery):

    booking_id = callback.data.split("_")[1]

    bookings = load_bookings()

    for booking in bookings:

        if booking["id"] == booking_id:

            booking["status"] = "confirmed"

    save_bookings(bookings)

    await callback.message.edit_text(
        f"✅ Бронь {booking_id} подтверждена"
    )

    await callback.answer("Подтверждено")

# =====================================================
# CANCEL
# =====================================================

@dp.callback_query(lambda c: c.data.startswith("cancel_"))
async def cancel_booking(callback: CallbackQuery):

    booking_id = callback.data.split("_")[1]

    bookings = load_bookings()

    for booking in bookings:

        if booking["id"] == booking_id:

            booking["status"] = "cancelled"

    save_bookings(bookings)

    await callback.message.edit_text(
        f"❌ Бронь {booking_id} отменена"
    )

    await callback.answer("Отменено")

# =====================================================
# START BOT
# =====================================================

async def start_bot():

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    await dp.start_polling(bot)

# =====================================================
# FASTAPI STARTUP
# =====================================================
# =====================================================
# АДМИНКА
# =====================================================

admin_state = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

# =====================================================
# КНОПКА АДМИНКИ
# =====================================================

@dp.message(lambda m: m.text == "🛠 Админка")
async def admin_panel(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    keyboard = ReplyKeyboardMarkup(

        keyboard=[

            [
                KeyboardButton(text="📋 Все брони"),
                KeyboardButton(text="📊 Статистика")
            ],

            [
                KeyboardButton(text="❌ Удалить бронь"),
                KeyboardButton(text="📅 Заблокировать даты")
            ],

            [
                KeyboardButton(text="🔓 Разблокировать даты"),
                KeyboardButton(text="💰 Изменить цену")
            ],

            [
                KeyboardButton(text="👤 Клиенты"),
                KeyboardButton(text="💬 Рассылка")
            ],

            [
                KeyboardButton(text="📈 Доход"),
                KeyboardButton(text="🕒 Последние брони")
            ],

            [
                KeyboardButton(text="🧹 Очистить брони")
            ]

        ],

        resize_keyboard=True
    )

    await message.answer(
        "⚙️ Панель администратора",
        reply_markup=keyboard
    )

# =====================================================
# ВСЕ БРОНИ
# =====================================================

@dp.message(lambda m: m.text == "📋 Все брони")
async def all_bookings(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    bookings = load_bookings()

    if not bookings:
        await message.answer("Броней пока нет")
        return

    text = "📋 ВСЕ БРОНИ\n\n"

    for b in bookings:

        text += f"""
ID: {b['id']}

📅 {b['checkin']} → {b['checkout']}
🌙 Ночей: {b['nights']}
💰 Сумма: {b['total']}€

-------------------
"""

    await message.answer(text)

# =====================================================
# СТАТИСТИКА
# =====================================================

@dp.message(lambda m: m.text == "📊 Статистика")
async def stats(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    bookings = load_bookings()

    total_bookings = len(bookings)

    total_income = sum(
        b.get("total", 0)
        for b in bookings
    )

    total_nights = sum(
        b.get("nights", 0)
        for b in bookings
    )

    await message.answer(
        f"""
📊 СТАТИСТИКА

📋 Броней: {total_bookings}

🌙 Ночей: {total_nights}

💰 Доход: {total_income}€
"""
    )

# =====================================================
# ДОХОД
# =====================================================

@dp.message(lambda m: m.text == "📈 Доход")
async def income(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    bookings = load_bookings()

    total_income = sum(
        b.get("total", 0)
        for b in bookings
    )

    await message.answer(
        f"💰 Общий доход: {total_income}€"
    )

# =====================================================
# ПОСЛЕДНИЕ БРОНИ
# =====================================================

@dp.message(lambda m: m.text == "🕒 Последние брони")
async def latest_bookings(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    bookings = load_bookings()

    if not bookings:
        await message.answer("Нет броней")
        return

    latest = bookings[-5:]

    text = "🕒 ПОСЛЕДНИЕ БРОНИ\n\n"

    for b in latest:

        text += f"""
ID: {b['id']}

📅 {b['checkin']} → {b['checkout']}
💰 {b['total']}€

-------------------
"""

    await message.answer(text)

# =====================================================
# КЛИЕНТЫ
# =====================================================

@dp.message(lambda m: m.text == "👤 Клиенты")
async def clients(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    bookings = load_bookings()

    total = len(bookings)

    await message.answer(
        f"👤 Всего клиентов: {total}"
    )

# =====================================================
# РАССЫЛКА
# =====================================================

@dp.message(lambda m: m.text == "💬 Рассылка")
async def mailing(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    admin_state[message.from_user.id] = "mailing"

    await message.answer(
        "Введите текст рассылки"
    )

@dp.message(lambda m: admin_state.get(m.from_user.id) == "mailing")
async def process_mailing(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    bookings = load_bookings()

    sent = 0

    for b in bookings:

        user_id = b.get("user_id")

        if user_id:

            try:

                await bot.send_message(
                    user_id,
                    message.text
                )

                sent += 1

            except:
                pass

    admin_state.pop(message.from_user.id, None)

    await message.answer(
        f"✅ Рассылка завершена\nОтправлено: {sent}"
    )

# =====================================================
# УДАЛЕНИЕ БРОНИ
# =====================================================

@dp.message(lambda m: m.text == "❌ Удалить бронь")
async def delete_booking(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    admin_state[message.from_user.id] = "delete_booking"

    await message.answer(
        "Введите ID брони"
    )

@dp.message(lambda m: admin_state.get(m.from_user.id) == "delete_booking")
async def process_delete(message: types.Message):

    bookings = load_bookings()

    booking_id = message.text.strip()

    new_bookings = [
        b for b in bookings
        if b["id"] != booking_id
    ]

    if len(new_bookings) == len(bookings):

        await message.answer(
            "❌ Бронь не найдена"
        )

        return

    save_bookings(new_bookings)

    admin_state.pop(message.from_user.id, None)

    await message.answer(
        "✅ Бронь удалена"
    )

# =====================================================
# ОЧИСТКА БРОНЕЙ
# =====================================================

@dp.message(lambda m: m.text == "🧹 Очистить брони")
async def clear_bookings(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    save_bookings([])

    await message.answer(
        "🧹 Все брони удалены"
    )

# =====================================================
# ИЗМЕНЕНИЕ ЦЕНЫ
# =====================================================

@dp.message(lambda m: m.text == "💰 Изменить цену")
async def change_price(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    admin_state[message.from_user.id] = "change_price"

    await message.answer(
        f"Текущая цена: {PRICE_PER_NIGHT}€\n\nВведите новую цену"
    )

@dp.message(lambda m: admin_state.get(m.from_user.id) == "change_price")
async def process_price(message: types.Message):

    global PRICE_PER_NIGHT

    try:

        PRICE_PER_NIGHT = int(message.text)

        admin_state.pop(message.from_user.id, None)

        await message.answer(
            f"✅ Новая цена: {PRICE_PER_NIGHT}€"
        )

    except:

        await message.answer(
            "Введите число"
        )
@app.on_event("startup")
async def startup_event():

    asyncio.create_task(start_bot())