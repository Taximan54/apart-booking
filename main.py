import os
import json
import uuid
import asyncio
from datetime import datetime, timedelta

from fastapi import FastAPI, Request
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
    InputMediaPhoto
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

PHOTOS = [
    "static/images/1.JPG",
    "static/images/2.JPG",
    "static/images/3.JPG"
]

# =====================================================
# FASTAPI
# =====================================================

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

# =====================================================
# TELEGRAM
# =====================================================

bot = Bot(token=BOT_TOKEN)
print(repr(BOT_TOKEN))
dp = Dispatcher()

# =====================================================
# МОДЕЛЬ
# =====================================================

class Booking(BaseModel):
    checkin: str
    checkout: str

# =====================================================
# РАБОТА С ФАЙЛОМ
# =====================================================

def load_bookings():
    try:
        with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_bookings(data):
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =====================================================
# ГЛАВНАЯ СТРАНИЦА
# =====================================================

@app.get("/", response_class=HTMLResponse)
async def home():

    html = """
<!DOCTYPE html>
<html lang="ru">
<head>

<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<title>ONE APART</title>

<style>

body{
    margin:0;
    font-family:Arial,sans-serif;
    background:#f3f3f3;
    color:#111;
}

.header{
    background:white;
    padding:24px;
    box-shadow:0 2px 10px rgba(0,0,0,0.05);
}

.logo{
    font-size:34px;
    font-weight:bold;
}

.sub{
    margin-top:6px;
    color:#777;
    font-size:15px;
}

.container{
    max-width:560px;
    margin:auto;
    padding:20px;
}

.gallery{
    display:flex;
    gap:14px;
    overflow-x:auto;
    margin-bottom:20px;
    scroll-snap-type:x mandatory;
}

.gallery img{
    width:100%;
    max-width:500px;
    height:300px;
    object-fit:cover;
    border-radius:24px;
    flex-shrink:0;
    scroll-snap-align:start;
}

.card{
    background:white;
    border-radius:28px;
    padding:24px;
    box-shadow:0 4px 20px rgba(0,0,0,0.06);
}

.calendar-header{
    display:flex;
    justify-content:space-between;
    align-items:center;
    margin-bottom:20px;
}

.month{
    font-size:30px;
    font-weight:bold;
}

.nav{
    width:52px;
    height:52px;
    border-radius:50%;
    border:none;
    background:#f0f0f0;
    font-size:24px;
    cursor:pointer;
}

.weekdays{
    display:grid;
    grid-template-columns:repeat(7,1fr);
    gap:10px;
    margin-bottom:14px;
    text-align:center;
    color:#777;
    font-size:14px;
}

.calendar{
    display:grid;
    grid-template-columns:repeat(7,1fr);
    gap:10px;
}

.day{
    aspect-ratio:1;
    border-radius:18px;
    background:white;
    border:2px solid #eee;
    display:flex;
    align-items:center;
    justify-content:center;
    font-weight:bold;
    cursor:pointer;
    transition:0.2s;
    font-size:18px;
}

.day:hover{
    transform:scale(1.05);
}

.busy{
    background:#ff6b6b;
    color:white;
    border:none;
    cursor:not-allowed;
}

.selected{
    background:black;
    color:white;
    border:none;
}

.range{
    background:#d9d9d9;
}

.past{
    opacity:0.4;
    cursor:not-allowed;
}

.info{
    margin-top:26px;
    text-align:center;
    line-height:1.7;
    font-size:18px;
}

.price{
    font-size:42px;
    font-weight:bold;
    margin-top:16px;
}

.btn{
    width:100%;
    margin-top:30px;
    border:none;
    border-radius:22px;
    padding:22px;
    background:black;
    color:white;
    font-size:22px;
    font-weight:bold;
    cursor:pointer;
}

.success{
    position:fixed;
    inset:0;
    background:rgba(0,0,0,0.7);
    display:none;
    justify-content:center;
    align-items:center;
    z-index:999;
}

.success-box{
    background:white;
    width:90%;
    max-width:420px;
    border-radius:28px;
    padding:34px;
    text-align:center;
}

.success-title{
    font-size:32px;
    font-weight:bold;
    margin-bottom:20px;
}

.success-text{
    font-size:20px;
    line-height:1.7;
}

.close{
    margin-top:24px;
    border:none;
    background:black;
    color:white;
    padding:16px 30px;
    border-radius:16px;
    font-size:18px;
}

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

<div class="success-title">
Бронь подтверждена
</div>

<div class="success-text" id="successText"></div>

<button class="close" onclick="closeSuccess()">
Закрыть
</button>

</div>

</div>

<script>

let busyDates = []

let checkin = null
let checkout = null

const today = new Date()
today.setHours(0,0,0,0)

let currentMonth = today.getMonth()
let currentYear = today.getFullYear()

const PRICE = 70

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

async function loadBusyDates(){

    const response = await fetch("/busy-dates")

    busyDates = await response.json()

    renderCalendar()
}

function isBusy(date){

    for(let b of busyDates){

        if(date < b.checkout && date >= b.checkin){
            return true
        }
    }

    return false
}

function renderCalendar(){

    const calendar = document.getElementById("calendar")

    calendar.innerHTML = ""

    document.getElementById("monthName").innerText =
    `${monthNames[currentMonth]} ${currentYear}`

    const daysInMonth =
    new Date(currentYear,currentMonth+1,0).getDate()

    for(let day=1; day<=daysInMonth; day++){

        const date =
        `${currentYear}-${String(currentMonth+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`

        const div = document.createElement("div")

        div.className = "day"

        div.innerText = day

        const dateObj = new Date(date)

        if(dateObj < today){

            div.classList.add("past")

        }else if(isBusy(date)){

            div.classList.add("busy")

        }else{

            div.onclick = ()=>selectDate(date)
        }

        if(checkin && date===checkin){
            div.classList.add("selected")
        }

        if(checkout && date===checkout){
            div.classList.add("selected")
        }

        if(checkin && checkout){

            if(date > checkin && date < checkout){
                div.classList.add("range")
            }
        }

        calendar.appendChild(div)
    }

    updateInfo()
}

function selectDate(date){

    if(isBusy(date)){
        return
    }

    const selectedDate = new Date(date)

    if(selectedDate < today){
        return
    }

    if(!checkin){

        checkin = date
        checkout = null

        renderCalendar()

        return
    }

    if(!checkout){

        if(date <= checkin){

            checkin = date
            renderCalendar()

            return
        }

        let current = new Date(checkin)

        while(current < new Date(date)){

            const currentDate =
            current.toISOString().split("T")[0]

            if(isBusy(currentDate)){

                alert("Диапазон содержит занятые даты")

                return
            }

            current.setDate(current.getDate()+1)
        }

        checkout = date

        renderCalendar()

        return
    }

    checkin = date
    checkout = null

    renderCalendar()
}

function updateInfo(){

    const info = document.getElementById("info")

    if(checkin && !checkout){

        info.innerHTML =
        `Заезд:<br><b>${checkin}</b>`

        return
    }

    if(checkin && checkout){

        const start = new Date(checkin)

        const end = new Date(checkout)

        const nights =
        (end-start)/(1000*60*60*24)

        const total =
        nights * PRICE

        info.innerHTML =
        `
        Заезд: <b>${checkin}</b><br>
        Выезд: <b>${checkout}</b><br>
        Ночей: <b>${nights}</b>

        <div class="price">
        ${total}€
        </div>
        `
    }
}

function prevMonth(){

    currentMonth--

    if(currentMonth < 0){

        currentMonth = 11
        currentYear--
    }

    renderCalendar()
}

function nextMonth(){

    currentMonth++

    if(currentMonth > 11){

        currentMonth = 0
        currentYear++
    }

    renderCalendar()
}

async function bookDate(){

    if(!checkin || !checkout){

        alert("Выберите даты")

        return
    }

    const response = await fetch("/book",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({
            checkin,
            checkout
        })
    })

    const data = await response.json()

    if(data.success){

        document.getElementById("success").style.display =
        "flex"

        document.getElementById("successText").innerHTML =
        `
        ID брони: <b>${data.booking_id}</b><br><br>
        ${checkin} → ${checkout}<br>
        ${data.nights} ночей<br><br>
        <b>${data.total}€</b>
        `

        loadBusyDates()

    }else{

        alert(data.message)
    }
}

function closeSuccess(){

    location.reload()
}

loadBusyDates()

</script>

</body>
</html>
"""

    return HTMLResponse(html)

# =====================================================
# ЗАНЯТЫЕ ДАТЫ
# =====================================================

@app.get("/busy-dates")
async def busy_dates():

    bookings = load_bookings()

    return JSONResponse(bookings)

# =====================================================
# БРОНИРОВАНИЕ
# =====================================================

@app.post("/book")
async def book(data: Booking):

    bookings = load_bookings()

    today = datetime.now().date()

    checkin = datetime.strptime(data.checkin, "%Y-%m-%d").date()
    checkout = datetime.strptime(data.checkout, "%Y-%m-%d").date()

    if checkin < today:
        return {
            "success": False,
            "message": "Нельзя бронировать прошедшие даты"
        }

    if checkout <= checkin:
        return {
            "success": False,
            "message": "Некорректные даты"
        }

    for b in bookings:

        booked_checkin = datetime.strptime(
            b["checkin"],
            "%Y-%m-%d"
        ).date()

        booked_checkout = datetime.strptime(
            b["checkout"],
            "%Y-%m-%d"
        ).date()

        if checkin < booked_checkout and checkout > booked_checkin:

            return {
                "success": False,
                "message": "Даты уже заняты"
            }

    nights = (checkout - checkin).days

    total = nights * PRICE_PER_NIGHT

    booking_id = str(uuid.uuid4())[:8]

    booking = {
        "id": booking_id,
        "checkin": str(checkin),
        "checkout": str(checkout),
        "nights": nights,
        "total": total
    }

    bookings.append(booking)

    save_bookings(bookings)

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
"""
        )

    return {
        "success": True,
        "booking_id": booking_id,
        "nights": nights,
        "total": total
    }

# =====================================================
# ФОТО
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
# TELEGRAM START
# =====================================================

@dp.message(CommandStart())
async def start(message: types.Message):

    keyboard = ReplyKeyboardMarkup(

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
                    text="📸 Фото квартиры"
                )
            ],

            [
                KeyboardButton(
                    text="📋 Описание квартиры"
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
# ФОТО КВАРТИРЫ
# =====================================================

@dp.message(lambda m: m.text == "📸 Фото квартиры")
async def photos(message: types.Message):

    await send_photos(message)

# =====================================================
# ОПИСАНИЕ КВАРТИРЫ
# =====================================================

@dp.message(lambda m: m.text == "📋 Описание квартиры")
async def apartment_description(message: types.Message):

    text = """С НАМИ КОМФОРТНО❣️

Добро пожаловать 🤗 в квартиру комфорт класса❗️

Абсолютная чистота - контроль качества уборки квартиры.🪷

Светлая, просторная квартира с новым качественным ремонтом рядом с центром Новосибирска на площади Калинина.

Высокий этаж, панорамное остекление, шикарный вид из окна.

Если вы гость в Новосибирске, находитесь в командировке или хотите отвлечься от рутины — наша студия идеальный выбор.

В квартире может проживать не более 2 гостей❗️

Условия для размещения с детьми не предусмотрены❗️"""

    await message.answer(text)

# =====================================================
# ЗАПУСК TELEGRAM
# =====================================================

async def start_bot():

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

# =====================================================
# FASTAPI STARTUP
# =====================================================

@app.on_event("startup")
async def startup_event():

    asyncio.create_task(start_bot())