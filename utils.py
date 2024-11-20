import aiohttp
import logging
from datetime import datetime, timedelta


async def check_site_availability(url: str) -> bool:
    """
    Проверяет доступность сайта через HTTP-запрос HEAD.
    Возвращает True, если сайт доступен (status code 200).
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url, timeout=5) as response:
                if response.status == 200:
                    return True
                else:
                    logging.warning(f"Сайт {url} недоступен. Код ответа: {response.status}")
                    return False
    except Exception as e:
        logging.error(f"Ошибка при проверке сайта {url}: {e}")
        return False



def calculate_next_date(current_date, recurrence_rule):
    """Вычисляет следующую дату на основе recurrence_rule."""
    if not recurrence_rule:
        return None, None  # Нет правила повторения

    rules = dict(item.split('=') for item in recurrence_rule.split(';'))
    freq = rules.get('FREQ')
    interval = int(rules.get('INTERVAL', 1))  # Интервал по умолчанию = 1
    count = int(rules.get('COUNT', 0))  # Количество повторений
    until = rules.get('UNTIL')  # Дата окончания в формате YYYYMMDDTHHMMSS

    # Если UNTIL задан, преобразуем его в datetime
    until_date = datetime.strptime(until, '%Y%m%dT%H%M%S') if until else None

    # Рассчитываем следующую дату
    if freq == "DAILY":
        next_date = current_date + timedelta(days=interval)
    elif freq == "WEEKLY":
        next_date = current_date + timedelta(weeks=interval)
    elif freq == "MONTHLY":
        next_date = current_date + timedelta(days=30 * interval)  # Упрощённый расчёт
    elif freq == "YEARLY":
        next_date = current_date + timedelta(days=365 * interval)  # Упрощённый расчёт
    elif freq == "HOURLY":
        next_date = current_date + timedelta(hours=interval)
    elif freq == "MINUTELY":
        next_date = current_date + timedelta(minutes=interval)
    elif freq == "SECONDLY":
        next_date = current_date + timedelta(seconds=interval)
    else:
        raise ValueError(f"Неизвестная частота FREQ: {freq}")

    # Проверяем ограничение UNTIL
    if until_date and next_date > until_date:
        return None, None

    # Обработка COUNT
    if 'COUNT' in rules:
        if count > 1:
            rules['COUNT'] = str(count - 1)
            updated_rule = ';'.join(f"{k}={v}" for k, v in rules.items())
            return next_date, updated_rule
        elif count == 1:
            # Последнее повторение, больше не повторяем
            return None, None
        elif count == 0:
            # COUNT=0 означает бесконечные повторения
            return next_date, recurrence_rule
        else:
            # COUNT отрицательный или некорректный
            return None, None
    else:
        # Если COUNT не задан, повторяем бесконечно
        return next_date, recurrence_rule



def calculate_next_month_date(current_date):
    """Вычисляет дату через месяц."""
    year = current_date.year + ((current_date.month) // 12)
    month = (current_date.month % 12) + 1
    day = current_date.day
    try:
        next_month_date = current_date.replace(year=year, month=month, day=day)
    except ValueError:
        # Если в следующем месяце нет такой даты, берём последний день месяца
        import calendar

        last_day = calendar.monthrange(year, month)[1]
        next_month_date = current_date.replace(year=year, month=month, day=last_day)
    return next_month_date


