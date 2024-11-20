from notifications.base import NotificationType
from telegram.error import TelegramError
import logging

class ReminderNotification(NotificationType):
    TYPE = "reminder"

    async def process(self, context):
        """Обрабатывает напоминание."""
        chat_id = self.get_chat_id()  # Получаем chat_id через базовый метод
        message_text = f"Напоминание:\n\n{self.format_message()}"

        try:
            # Отправляем сообщение
            await context.bot.send_message(chat_id=chat_id, text=message_text)
            logging.info(f"Напоминание отправлено в чат {chat_id}: {self.notification.message}")
        except TelegramError as e:
            logging.error(f"Не удалось отправить сообщение в чат {chat_id}: {e}")
