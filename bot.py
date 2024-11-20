# bot.py
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
)
from dotenv import load_dotenv
from database import get_db
from models import User, Notification
from utils import calculate_next_month_date

# Загрузка переменных окружения
load_dotenv()

class SendAndErrorFilter(logging.Filter):
    def filter(self, record):
        if record.levelno == logging.ERROR:
            return True
        elif record.levelno == logging.INFO and record.getMessage().startswith("SEND:"):
            return True
        return False

# Настройка логирования
logger = logging.getLogger("bot_logger")
logger.setLevel(logging.INFO)  # Уровень логирования установлен на INFO

# Создаём обработчик с ротацией
handler = RotatingFileHandler(
    "bot.log",
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=5,         # Хранить 5 резервных копий
    encoding='utf-8'
)

# Настройка формата
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

# Добавляем фильтр
handler.addFilter(SendAndErrorFilter())

# Добавляем обработчик к логгеру
logger.addHandler(handler)

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOSCOW_TZ = ZoneInfo("Europe/Moscow")


# Команда /start: регистрация пользователя
async def start_handler(update: Update, context: CallbackContext):
    """Регистрация пользователя в базе данных."""
    chat_id = update.message.chat_id
    username = update.message.from_user.username
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name

    db = next(get_db())  # Получаем сессию базы данных
    try:
        user = db.query(User).filter_by(chat_id=chat_id).first()
        if not user:
            user = User(
                chat_id=chat_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            db.add(user)
            db.commit()
            logger.info(f"SEND: Новый пользователь зарегистрирован: {username}")

        await update.message.reply_text("Добро пожаловать! Вы зарегистрированы.")
    except Exception as e:
        logger.error(f"Ошибка при регистрации пользователя: {e}")
        db.rollback()  # Откат изменений при ошибке
    finally:
        db.close()  # Закрываем сессию


async def notification_scheduler(context: CallbackContext):
    """Ищет запланированные уведомления и выполняет их."""
    now = datetime.now(MOSCOW_TZ)
    time_limit = now + timedelta(minutes=1)  # Добавляем запас времени
    db = next(get_db())

    try:
        # Сбрасываем confirmed для уведомлений, дата которых наступила и они были подтверждены
        notifications_to_reset = db.query(Notification).filter(
            Notification.notify_date <= now, Notification.confirmed == True
        ).all()
        for notification in notifications_to_reset:
            notification.confirmed = False
            db.commit()

        # Получаем все неподтверждённые уведомления, которые нужно обработать
        notifications = db.query(Notification).filter(
            Notification.notify_date <= time_limit, Notification.confirmed == False
        ).all()

        for notification in notifications:
            try:
                chat_id = notification.target_chat_id or int(os.getenv("CHAT_ID"))
                message_text = notification.message

                # Удаляем предыдущее сообщение, если оно было отправлено
                if notification.last_message_id:
                    try:
                        await context.bot.delete_message(
                            chat_id=chat_id, message_id=notification.last_message_id
                        )
                        logger.info(
                            f"SEND: Удалено предыдущее сообщение с ID {notification.last_message_id}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Не удалось удалить сообщение {notification.last_message_id}: {e}"
                        )

                # Кнопка "ОК"
                keyboard = [
                    [InlineKeyboardButton("ОК", callback_data=f"confirm_{notification.id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                # Отправляем новое сообщение с кнопкой
                sent_message = await context.bot.send_message(
                    chat_id=chat_id, text=message_text, reply_markup=reply_markup
                )
                logger.info(
                    f"SEND: Отправлено новое сообщение с ID {sent_message.message_id}"
                )

                # Обновляем last_message_id
                notification.last_message_id = sent_message.message_id

                # Если кнопка не нажата, планируем повтор через 5 минут
                notification.notify_date = now + timedelta(minutes=5)

                db.commit()
            except Exception as e:
                logger.error(f"Ошибка при обработке уведомления {notification.id}: {e}")
                db.rollback()

    except Exception as e:
        logger.error(f"Ошибка в notification_scheduler: {e}")
        db.rollback()
    finally:
        db.close()


async def confirm_notification(update: Update, context: CallbackContext):
    """Обрабатывает подтверждение уведомления."""
    query = update.callback_query
    notification_id = int(query.data.split("_")[1])  # Получаем ID уведомления

    db = next(get_db())
    try:
        # Получаем уведомление из базы данных
        notification = db.query(Notification).filter_by(id=notification_id).first()
        if notification:
            # Переносим дату уведомления на месяц вперед
            next_month_date = calculate_next_month_date(notification.notify_date)
            notification.notify_date = next_month_date
            notification.next_notify_date = next_month_date
            notification.confirmed = True
            # Сбрасываем last_message_id, так как сообщение обновлено
            notification.last_message_id = None
            db.commit()
            logger.info(
                f"SEND: Уведомление {notification_id} подтверждено и перенесено на {next_month_date}"
            )

            # Обновляем сообщение
            new_message_text = (
                f"{notification.message}\n\n"
                f"Следующее уведомление запланировано на: {next_month_date.strftime('%d.%m.%Y %H:%M')}"
            )
            await query.edit_message_text(text=new_message_text)

            # Отправляем уведомление пользователю
            await query.answer(
                "Уведомление подтверждено. Оно будет перенесено на следующий месяц."
            )
        else:
            await query.answer("Уведомление не найдено.")
    except Exception as e:
        logger.error(f"Ошибка при подтверждении уведомления: {e}")
        db.rollback()
        await query.answer("Ошибка при подтверждении уведомления.")
    finally:
        db.close()


# Запуск бота
def main():
    """Главная точка входа для запуска Telegram-бота."""
    logger.info("SEND: Запуск Telegram-бота")

    # Создаем приложение с явной активацией job_queue
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(lambda app: app.job_queue.start())
        .build()
    )

    # Добавляем команды
    application.add_handler(CommandHandler("start", start_handler))

    # Добавляем обработчик кнопки "ОК"
    application.add_handler(
        CallbackQueryHandler(confirm_notification, pattern="^confirm_")
    )

    # Планировщик: проверка уведомлений каждые 5 секунд (можно изменить при необходимости)
    application.job_queue.run_repeating(
        notification_scheduler,
        interval=5,  # Проверка уведомлений каждые 5 секунд
        first=timedelta(seconds=10),
    )

    logger.info("SEND: Бот запущен и готов к работе")
    application.run_polling()


if __name__ == "__main__":
    main()
