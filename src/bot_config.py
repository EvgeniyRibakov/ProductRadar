"""
Конфигурация Telegram бота
"""

import os
from pathlib import Path
from typing import List, Optional

# Путь к .env файлу
ENV_FILE = Path(__file__).parent.parent / "config" / ".env"

def load_env_file():
    """Загрузить переменные из config/.env"""
    if not ENV_FILE.exists():
        import logging
        logging.warning(f"Файл .env не найден: {ENV_FILE}")
        return {}
    
    env_vars = {}
    try:
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                original_line = line
                line = line.strip()
                
                # Пропускаем пустые строки и комментарии
                if not line or line.startswith("#"):
                    continue
                
                # Проверяем наличие =
                if "=" not in line:
                    continue
                
                # Разделяем на ключ и значение
                parts = line.split("=", 1)
                if len(parts) != 2:
                    continue
                
                key = parts[0].strip()
                value = parts[1].strip()
                
                # Убираем кавычки если есть
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # Сохраняем только если ключ не пустой
                # Значение может быть пустым (но это нежелательно)
                if key:
                    env_vars[key] = value
                    
    except Exception as e:
        import logging
        logging.error(f"Ошибка при чтении .env файла: {e}")
    
    return env_vars

# Загружаем переменные
_env = load_env_file()

# Отладочная информация
import logging
_logger = logging.getLogger("BotConfig")

# Инициализируем логгер только если logging настроен
try:
    _logger.debug(f"Загружено переменных из .env: {len(_env)}")
    _logger.debug(f"Ключи: {list(_env.keys())}")
except:
    # Если logging не настроен, просто пропускаем
    pass

# Токен бота
TELEGRAM_BOT_TOKEN = _env.get("TG_API_TOKEN", os.getenv("TG_API_TOKEN", ""))
if not TELEGRAM_BOT_TOKEN:
    # Пробуем альтернативные варианты названия
    TELEGRAM_BOT_TOKEN = _env.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_TOKEN = _env.get("BOT_TOKEN", "")

# Разрешенные пользователи
_allowed_users_str = _env.get("ID_TG", os.getenv("ID_TG", ""))
if not _allowed_users_str:
    # Пробуем альтернативные варианты
    _allowed_users_str = _env.get("TELEGRAM_ALLOWED_USERS", "")
    _allowed_users_str = _env.get("ALLOWED_USERS", "")

TELEGRAM_ALLOWED_USERS: List[int] = []
if _allowed_users_str:
    try:
        # Поддержка нескольких user_id через запятую
        TELEGRAM_ALLOWED_USERS = [
            int(uid.strip()) for uid in _allowed_users_str.split(",") if uid.strip()
        ]
        try:
            _logger.debug(f"Загружено user_id: {TELEGRAM_ALLOWED_USERS}")
        except:
            pass
    except ValueError as e:
        try:
            _logger.error(f"Ошибка при парсинге user_id: {e}, значение: '{_allowed_users_str}'")
        except:
            pass

def validate_config() -> tuple[bool, Optional[str]]:
    """Проверка конфигурации"""
    import logging
    _logger = logging.getLogger("BotConfig")
    
    try:
        _logger.debug(f"Проверка конфигурации:")
        _logger.debug(f"  TELEGRAM_BOT_TOKEN: {'установлен' if TELEGRAM_BOT_TOKEN else 'НЕ установлен'} (длина: {len(TELEGRAM_BOT_TOKEN)})")
        _logger.debug(f"  TELEGRAM_ALLOWED_USERS: {TELEGRAM_ALLOWED_USERS}")
        _logger.debug(f"  Путь к .env: {ENV_FILE}")
        _logger.debug(f"  Файл существует: {ENV_FILE.exists()}")
        _logger.debug(f"  Загруженные ключи из .env: {list(_env.keys())}")
    except:
        pass
    
    if not TELEGRAM_BOT_TOKEN:
        error_msg = f"TG_API_TOKEN не установлен в config/.env"
        error_msg += f"\n  Файл: {ENV_FILE}"
        error_msg += f"\n  Существует: {ENV_FILE.exists()}"
        if ENV_FILE.exists():
            error_msg += f"\n  Найденные ключи в .env: {list(_env.keys())}"
        return False, error_msg
    
    if not TELEGRAM_ALLOWED_USERS:
        error_msg = f"ID_TG не установлен в config/.env"
        error_msg += f"\n  Файл: {ENV_FILE}"
        error_msg += f"\n  Существует: {ENV_FILE.exists()}"
        if ENV_FILE.exists():
            error_msg += f"\n  Найденные ключи в .env: {list(_env.keys())}"
            error_msg += f"\n  Значение ID_TG из .env: '{_env.get('ID_TG', 'НЕ НАЙДЕНО')}'"
        return False, error_msg
    
    return True, None

def is_user_allowed(user_id: int) -> bool:
    """Проверить, разрешен ли пользователь"""
    return user_id in TELEGRAM_ALLOWED_USERS

