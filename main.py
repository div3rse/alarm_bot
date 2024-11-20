# main.py
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from fastapi import FastAPI, Request, Form, Depends, HTTPException, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from database import get_db
from models import User, Notification

# Загрузка переменных окружения
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import aiofiles

active_connections = []
last_log_size = 0


load_dotenv()

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Отправляем все исторические логи новому подключению
        await self.send_existing_logs(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_existing_logs(self, websocket: WebSocket):
        logfile = os.path.join(BASE_DIR, "bot.log")
        if not os.path.exists(logfile):
            print(f"Файл логов {logfile} не найден.")
            return
        try:
            async with aiofiles.open(logfile, "r", encoding="utf-8") as file:
                lines = await file.readlines()
                print(f"Чтение {len(lines)} строк из логов.")
                for line in lines:
                    if "SEND:" in line or "ERROR:" in line:
                        await websocket.send_text(line.strip())
        except Exception as e:
            print(f"Ошибка при отправке существующих логов: {e}")

    async def broadcast(self, message: str):
        for connection in self.active_connections.copy():
            try:
                if "SEND:" in message or "ERROR:" in message:
                    await connection.send_text(message)
            except Exception as e:
                print(f"Ошибка при отправке сообщения: {e}")
                self.disconnect(connection)


manager = ConnectionManager()



# Настройка секретного ключа для сессий
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
# Настройка шаблонов
templates = Jinja2Templates(directory="templates")

# Простая авторизация
def is_authenticated(request: Request):
    return request.session.get("logged_in") == True

# Главная страница - перенаправление на страницу входа
@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/login")

# Страница входа
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# Обработка входа
@app.post("/login", response_class=HTMLResponse)
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    correct_username = os.getenv("ADMIN_USERNAME", "admin")
    correct_password = os.getenv("ADMIN_PASSWORD", "admin")

    if username == correct_username and password == correct_password:
        request.session["logged_in"] = True
        return RedirectResponse(url="/dashboard", status_code=302)
    else:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})

# Страница выхода
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    user_count = db.query(User).count()
    notification_count = db.query(Notification).count()
    return templates.TemplateResponse("dashboard.html", {"request": request, "user_count": user_count, "notification_count": notification_count})


# Управление пользователями
@app.get("/users", response_class=HTMLResponse)
async def users(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")

    db = next(get_db())
    users = db.query(User).all()
    return templates.TemplateResponse("users.html", {"request": request, "users": users})

# Добавление пользователя
@app.get("/users/add", response_class=HTMLResponse)
async def add_user_form(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("add_user.html", {"request": request})

@app.post("/users/add")
async def add_user(request: Request, chat_id: int = Form(...), username: str = Form(...), first_name: str = Form(...), last_name: str = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    user = User(chat_id=chat_id, username=username, first_name=first_name, last_name=last_name)
    db.add(user)
    db.commit()
    return RedirectResponse(url="/users", status_code=302)

# Редактирование пользователя
@app.get("/users/edit/{user_id}", response_class=HTMLResponse)
async def edit_user_form(request: Request, user_id: int = Path(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        return RedirectResponse(url="/users")
    return templates.TemplateResponse("edit_user.html", {"request": request, "user": user})

@app.post("/users/edit/{user_id}")
async def edit_user(request: Request, user_id: int = Path(...), chat_id: int = Form(...), username: str = Form(...), first_name: str = Form(...), last_name: str = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        user.chat_id = chat_id
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        db.commit()
    return RedirectResponse(url="/users", status_code=302)

# Удаление пользователя
@app.get("/users/delete/{user_id}")
async def delete_user(request: Request, user_id: int = Path(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        db.delete(user)
        db.commit()
    return RedirectResponse(url="/users", status_code=302)

# Управление уведомлениями
@app.get("/notifications", response_class=HTMLResponse)
async def notifications(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")

    db = next(get_db())
    notifications = db.query(Notification).all()
    return templates.TemplateResponse("notifications.html", {"request": request, "notifications": notifications})

# Добавление уведомления
@app.get("/notifications/add", response_class=HTMLResponse)
async def add_notification_form(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("add_notification.html", {"request": request})

@app.post("/notifications/add")
async def add_notification(request: Request, type: str = Form(...), message: str = Form(...), notify_date: str = Form(...), is_recurring: str = Form(None)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    try:
        notify_date_parsed = datetime.strptime(notify_date, "%d.%m.%Y %H:%M")
        notification = Notification(
            type=type,
            message=message,
            notify_date=notify_date_parsed,
            is_recurring=bool(is_recurring)
        )
        db.add(notification)
        db.commit()
    except Exception as e:
        print(f"Ошибка при добавлении уведомления: {e}")
    return RedirectResponse(url="/notifications", status_code=302)

# Редактирование уведомления
@app.get("/notifications/edit/{notification_id}", response_class=HTMLResponse)
async def edit_notification_form(request: Request, notification_id: int = Path(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    notification = db.query(Notification).filter_by(id=notification_id).first()
    if not notification:
        return RedirectResponse(url="/notifications")
    return templates.TemplateResponse("edit_notification.html", {"request": request, "notification": notification})

@app.post("/notifications/edit/{notification_id}")
async def edit_notification(request: Request, notification_id: int = Path(...), type: str = Form(...), message: str = Form(...), notify_date: str = Form(...), is_recurring: str = Form(None)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    try:
        notification = db.query(Notification).filter_by(id=notification_id).first()
        if notification:
            notification.type = type
            notification.message = message
            notification.notify_date = datetime.strptime(notify_date, "%d.%m.%Y %H:%M")
            notification.is_recurring = bool(is_recurring)
            db.commit()
    except Exception as e:
        print(f"Ошибка при редактировании уведомления: {e}")
    return RedirectResponse(url="/notifications", status_code=302)

# Удаление уведомления
@app.get("/notifications/delete/{notification_id}")
async def delete_notification(request: Request, notification_id: int = Path(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    db = next(get_db())
    notification = db.query(Notification).filter_by(id=notification_id).first()
    if notification:
        db.delete(notification)
        db.commit()
    return RedirectResponse(url="/notifications", status_code=302)


@app.get("/logs", response_class=HTMLResponse)
async def logs_page(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("logs.html", {"request": request})

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Ожидаем сообщений от клиента, но не используем
    except WebSocketDisconnect:
        manager.disconnect(websocket)


class LogHandler(FileSystemEventHandler):
    def __init__(self, filepath, manager, loop):
        self.filepath = filepath
        self.manager = manager
        self.loop = loop
        self._file = open(self.filepath, 'r', encoding='utf-8')
        self._file.seek(0, os.SEEK_END)

    def on_modified(self, event):
        if event.src_path == self.filepath:
            for line in self._file:
                if "SEND:" in line or "ERROR:" in line:
                    print(f"Отправка лога через WebSocket: {line.strip()}")
                    # Используем run_coroutine_threadsafe для запуска корутины в основном цикле
                    asyncio.run_coroutine_threadsafe(
                        self.manager.broadcast(line.strip()),
                        self.loop
                    )

    def on_created(self, event):
        if event.src_path == self.filepath:
            self._file = open(self.filepath, 'r', encoding='utf-8')
            self._file.seek(0, os.SEEK_END)

async def run_observer(observer):
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        observer.stop()
    observer.join()

@app.on_event("startup")
async def startup_event():
    # Получаем основной цикл событий
    loop = asyncio.get_running_loop()
    # Запуск наблюдателя за лог-файлом
    observer = Observer()
    log_dir = BASE_DIR
    logfile = os.path.join(log_dir, "bot.log")
    handler = LogHandler(logfile, manager, loop)
    observer.schedule(handler, path=log_dir, recursive=False)
    observer.start()
    # Запуск наблюдателя в отдельной задаче
    asyncio.create_task(run_observer(observer))