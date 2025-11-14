"""
Конфигурация проекта - загрузка настроек и констант
"""

import os
from pathlib import Path
from typing import Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Если python-dotenv не установлен, просто пропускаем
    pass


# Базовые пути
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"
LOGS_DIR = PROJECT_ROOT / "logs"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# Создаем необходимые директории
LOGS_DIR.mkdir(exist_ok=True)
SCREENSHOTS_DIR.mkdir(exist_ok=True)

# Pipiads настройки
PIPIADS_EMAIL = os.getenv("PIPIADS_EMAIL", "aiagentforcosmobeauty@gmail.com")
PIPIADS_PASSWORD = os.getenv("PIPIADS_PASSWORD", ")ZRg8,tbOtsR>)U")

# Начальный URL Pipiads
PIPIADS_INITIAL_URL = os.getenv(
    "PIPIADS_INITIAL_URL",
    "https://www.pipiads.com/ru/tiktok-shop-product?time=7&categorize=601595,601733,873480,601613,601615,601616,601619,601602,601608,601609,601611,601610,601646,873736,601506,601511,2169232,978056,601490,601493,601492,601495,601494,601498,1003784,873864,873608,601686,601565,1004808,601627,601681,601644,601513,601516,981512,601469,806160,700789,1004168,601582,601585,601587,601586,601588,853264,601558,601560,601550,601552,601554,601556,601555,601529,601534,853520,601618,875144,601462,601461,601463,601737,874888&search_type=1&sales_trend=1&current_page=1&page_size=20&sort=5&sort_type=desc"
)

# Google Sheets настройки
GOOGLE_SHEETS_ID = os.getenv(
    "GOOGLE_SHEETS_ID",
    "1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ"
)
GOOGLE_SHEETS_SHEET_NAME = os.getenv(
    "GOOGLE_SHEETS_SHEET_NAME",
    "шаблон выгрузуи 1.0"
)
GOOGLE_CREDENTIALS_PATH = CONFIG_DIR / "google-credentials.json"

# Параметры фильтрации видео
MIN_IMPRESSIONS = int(os.getenv("MIN_IMPRESSIONS", "5000"))  # Минимум 5K impressions
PRIORITY_IMPRESSIONS = int(os.getenv("PRIORITY_IMPRESSIONS", "100000"))
DAYS_BACK = int(os.getenv("DAYS_BACK", "30"))  # Видео не старше 30 дней

# Настройки браузера
BROWSER_HEADLESS = os.getenv("BROWSER_HEADLESS", "true").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30000"))  # 30 секунд
RANDOM_DELAY_MIN = int(os.getenv("RANDOM_DELAY_MIN", "2"))  # секунды
RANDOM_DELAY_MAX = int(os.getenv("RANDOM_DELAY_MAX", "5"))  # секунды

# Retry настройки
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY_BASE = int(os.getenv("RETRY_DELAY_BASE", "2"))  # секунды

# Структура Google Sheets
SHEET_START_ROW = 3  # Начальная строка для данных (строка 2 - пример, не трогать)
SHEET_SKIP_COLUMN = "C"  # Столбец C не трогать (для другого ИИ)

# Столбцы Google Sheets
SHEET_COLUMNS = {
    "product_number": "A",
    "product_name": "B",
    "category": "D",
    "pipiads_link": "E",
    # Видео 1
    "video1_tiktok": "F",
    "video1_impression": "G",
    "video1_script": "H",
    "video1_hook": "I",
    "video1_audience": "J",
    "video1_country": "K",
    "video1_first_seen": "L",
    # Видео 2
    "video2_tiktok": "M",
    "video2_impression": "N",
    "video2_script": "O",
    "video2_hook": "P",
    "video2_audience": "Q",
    "video2_country": "R",
    "video2_first_seen": "S",
    # Видео 3
    "video3_tiktok": "T",
    "video3_impression": "U",
    "video3_script": "V",
    "video3_hook": "W",
    "video3_audience": "X",
    "video3_country": "Y",
    "video3_first_seen": "Z",
}


def get_google_credentials_path() -> Path:
    """Возвращает путь к файлу credentials Google Sheets"""
    return GOOGLE_CREDENTIALS_PATH


def validate_config() -> Tuple[bool, Optional[str]]:
    """
    Валидация конфигурации
    
    Returns:
        (is_valid, error_message)
    """
    # Проверка credentials файла
    if not GOOGLE_CREDENTIALS_PATH.exists():
        return False, f"Google credentials файл не найден: {GOOGLE_CREDENTIALS_PATH}"
    
    # Проверка обязательных параметров
    if not PIPIADS_EMAIL or not PIPIADS_PASSWORD:
        return False, "Pipiads email или пароль не установлены"
    
    if not GOOGLE_SHEETS_ID:
        return False, "Google Sheets ID не установлен"
    
    return True, None

