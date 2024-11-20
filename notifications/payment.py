from notifications.base import NotificationType
from telegram.error import TelegramError
import logging

class PaymentNotification(NotificationType):
    TYPE = "payment"

    async def process(self, context):
        """Обрабатывает уведомление об оплате."""
        chat_id = self.get_chat_id()  # Получаем chat_id через базовый метод
        message_text = f"Уведомление об оплате:\n\n{self.format_message()}"

        try:
            # Отправляем сообщение
            await context.bot.send_message(chat_id=chat_id, text=message_text)
            logging.info(f"Уведомление отправлено в чат {chat_id}: {self.notification.message}")
        except TelegramError as e:
            logging.error(f"Не удалось отправить сообщение в чат {chat_id}: {e}")
