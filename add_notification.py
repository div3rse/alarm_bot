from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from database import get_db, Notification
from sqlalchemy.orm import sessionmaker

# Установите временную зону
MOSCOW_TZ = ZoneInfo("Europe/Moscow")

def add_notification_example():
    db = next(get_db())  # Получаем сессию базы данных

    try:
        # Пример добавления уведомления об оплате
        notify_date = datetime.now(MOSCOW_TZ) + timedelta(minutes=1)  # Через 1 минуту

        new_notification = Notification(
            user_id=None,
            type="reminder",  # Или другой тип
            message="Ваше напоминание TYT.",
            notify_date=notify_date,
            is_recurring=True,
            confirmed=False,
            target_chat_id=None,
            last_message_id=None,
            next_notify_date=None
        )

        db.add(new_notification)
        db.commit()
        print("Уведомление добавлено в базу данных!")
    except Exception as e:
        db.rollback()  # Откат изменений в случае ошибки
        print(f"Ошибка при добавлении уведомления: {e}")
    finally:
        db.close()  # Закрываем сессию


if __name__ == "__main__":
    add_notification_example()