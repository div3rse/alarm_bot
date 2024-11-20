# Alarm Bot
Админ панель + телеграм бот для формирования напоминаний.

## Установка

```bash
git clone https://github.com/div3rse/alarm_bot.git
cd alarm_bot
python3 -m venv venv
source venv/bin/activate  # Для Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

Заполняем данные в .env

## Запуск бота 
python3 bot.py
или
python bot.py

## Запуск панельки
uvicorn main:app --reload
