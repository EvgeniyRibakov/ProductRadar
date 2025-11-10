"""
Валидация данных - проверка и преобразование данных
"""

from datetime import datetime, timedelta
from typing import Optional
import re


def parse_video_date(date_string: str) -> Optional[datetime]:
    """
    Парсит дату в формате "Oct 27 2025"
    
    Args:
        date_string: Строка с датой в формате "Oct 27 2025" или "N/A"
    
    Returns:
        Объект datetime или None если дата невалидна
    """
    if not date_string or date_string.strip() == "N/A":
        return None
    
    # Словарь месяцев
    months = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6,
        "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12
    }
    
    # Разбиваем строку
    parts = date_string.strip().split()
    if len(parts) != 3:
        return None
    
    month_str, day_str, year_str = parts
    
    # Получаем месяц
    month = months.get(month_str)
    if month is None:
        return None
    
    # Парсим день и год
    try:
        day = int(day_str)
        year = int(year_str)
    except ValueError:
        return None
    
    # Валидация
    if not (1 <= day <= 31) or year < 2020 or year > 2100:
        return None
    
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def is_date_within_days(date: Optional[datetime], days: int = 7) -> bool:
    """
    Проверяет, что дата находится в пределах последних N дней
    
    Args:
        date: Дата для проверки
        days: Количество дней назад
    
    Returns:
        True если дата в пределах периода, False иначе
    """
    if date is None:
        return False
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_date = today - timedelta(days=days)
    
    return date >= cutoff_date


def validate_impressions(impressions: Optional[int], min_value: int = 50000) -> bool:
    """
    Валидация количества показов (impressions)
    
    Args:
        impressions: Количество показов
        min_value: Минимальное значение
    
    Returns:
        True если impressions >= min_value
    """
    if impressions is None:
        return False
    
    return impressions >= min_value


def parse_impressions(impressions_str: str) -> Optional[int]:
    """
    Парсит строку с impressions (может быть "15.1K", "101300", "15,100" и т.д.)
    
    Args:
        impressions_str: Строка с количеством показов
    
    Returns:
        Число impressions или None
    """
    if not impressions_str or impressions_str.strip() == "N/A":
        return None
    
    # Убираем пробелы и запятые
    clean_str = impressions_str.strip().replace(",", "").replace(" ", "")
    
    # Обработка формата "15.1K", "1.5M" и т.д.
    if clean_str.upper().endswith("K"):
        try:
            number = float(clean_str[:-1])
            return int(number * 1000)
        except ValueError:
            return None
    elif clean_str.upper().endswith("M"):
        try:
            number = float(clean_str[:-1])
            return int(number * 1000000)
        except ValueError:
            return None
    
    # Обычное число
    try:
        return int(float(clean_str))
    except ValueError:
        return None


def validate_url(url: str) -> bool:
    """
    Валидация URL
    
    Args:
        url: URL для проверки
    
    Returns:
        True если URL валиден
    """
    if not url or url.strip() == "N/A":
        return False
    
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return bool(url_pattern.match(url.strip()))


def validate_video_date_string(date_string: str, days_back: int = 7) -> tuple[bool, Optional[str]]:
    """
    Валидация строки с датой видео (полная проверка)
    
    Args:
        date_string: Строка с датой в формате "Oct 27 2025"
        days_back: Количество дней назад для проверки
    
    Returns:
        (is_valid, error_message)
    """
    if not date_string or date_string.strip() == "N/A":
        return False, "Дата отсутствует или N/A"
    
    parsed_date = parse_video_date(date_string)
    if parsed_date is None:
        return False, f"Не удалось распарсить дату: {date_string}"
    
    if not is_date_within_days(parsed_date, days_back):
        return False, f"Дата {date_string} старше {days_back} дней"
    
    return True, None


def format_audience(age: Optional[str], platform: Optional[str] = None) -> str:
    """
    Форматирует строку аудитории в формате "35-45 Android"
    
    Args:
        age: Возраст аудитории (например "35-45")
        platform: Платформа (например "Android")
    
    Returns:
        Отформатированная строка или "N/A"
    """
    if not age or age.strip() == "N/A":
        return "N/A"
    
    parts = [age.strip()]
    if platform and platform.strip() and platform.strip() != "N/A":
        parts.append(platform.strip())
    
    result = " ".join(parts).strip()
    return result if result else "N/A"


def format_impressions(impressions: Optional[int]) -> str:
    """
    Форматирует число impressions в формат "170.6K" или "339.9M"
    
    Args:
        impressions: Число impressions
    
    Returns:
        Отформатированная строка (например "170.6K", "339.9M") или "N/A"
    """
    if impressions is None or impressions <= 0:
        return "N/A"
    
    # Если >= 1 миллион, форматируем как M
    if impressions >= 1_000_000:
        millions = impressions / 1_000_000
        # Округляем до 1 знака после запятой
        if millions >= 100:
            return f"{int(millions)}M"
        else:
            return f"{millions:.1f}M".rstrip('0').rstrip('.')
    
    # Если >= 1 тысяча, форматируем как K
    elif impressions >= 1_000:
        thousands = impressions / 1_000
        # Округляем до 1 знака после запятой
        if thousands >= 100:
            return f"{int(thousands)}K"
        else:
            return f"{thousands:.1f}K".rstrip('0').rstrip('.')
    
    # Меньше 1000 - просто число
    else:
        return str(impressions)




