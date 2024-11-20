from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
import logging
import os

class NotificationType:
    def __init__(self, notification):
        self.notification = notification

    def get_chat_id(self):
        """Получает chat_id для уведомления."""
        return self.notification.target_chat_id or os.getenv("CHAT_ID")

    def format_message(self):
        """Возвращает текст сообщения."""
        return (
            f"{self.notification.message}\n"
            f"Дата и время: {self.notification.notify_date.strftime('%d.%m.%Y %H:%M')}"
        )

    def get_keyboard(self):
        """Создаёт клавиатуру с кнопкой 'ОК'."""
        keyboard = [
            [InlineKeyboardButton("ОК", callback_data=f"confirm_{self.notification.id}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def process(self, context):
        """Отправляет сообщение с кнопкой 'ОК'. Реализация в дочерних классах."""
        chat_id = self.get_chat_id()
        message_text = self.format_message()
        reply_markup = self.get_keyboard()

        try:
            await context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)
            logging.info(f"Уведомление отправлено в чат {chat_id}: {self.notification.message}")
        except TelegramError as e:
            logging.error(f"Не удалось отправить сообщение в чат {chat_id}: {e}")
