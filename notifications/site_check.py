from notifications.base import NotificationType
from utils import check_site_availability

class SiteCheckNotification(NotificationType):
    TYPE = "site_check"

    async def process(self, context):
        """Проверяет доступность сайта и отправляет результат."""
        notification = self.notification
        url = notification.message
        chat_id = notification.target_chat_id or notification.user.chat_id

        is_available = await check_site_availability(url)

        result_message = (
            f"Сайт {url} доступен" if is_available
            else f"Сайт {url} недоступен"
        )

        await context.bot.send_message(
            chat_id=chat_id,
            text=result_message
        )
        print(f"Результат проверки сайта {url} отправлен в чат {chat_id}: {result_message}")
