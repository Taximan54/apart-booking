from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import json
import os

app = FastAPI()

BOOKINGS_FILE = "bookings.json"

if not os.path.exists(BOOKINGS_FILE):
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def load_bookings():
    with open(BOOKINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_bookings(data):
    with open(BOOKINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return FileResponse("static/index.html")

@app.get("/busy-dates")
async def busy_dates():
    return JSONResponse(load_bookings())

@app.post("/book")
async def book(request: Request):

    data = await request.json()

    bookings = load_bookings()

    checkin = data.get("checkin")
    checkout = data.get("checkout")

    if not checkin or not checkout:
        return JSONResponse({
            "success": False,
            "message": "Нет дат"
        })

    bookings.append({
        "checkin": checkin,
        "checkout": checkout
    })

    save_bookings(bookings)

    return JSONResponse({
        "success": True
    })