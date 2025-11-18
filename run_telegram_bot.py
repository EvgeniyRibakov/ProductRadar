"""
Точка входа для запуска Telegram бота
"""

import sys
from pathlib import Path
from datetime import datetime
import logging

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent))

from src.telegram_bot import run_bot
from src import bot_config
from src import logger

# Настройка логирования - только важное
logging.basicConfig(
    level=logging.INFO,  # INFO вместо DEBUG
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Отключаем избыточные логи от библиотек
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

log = logger.get_logger("Main")

if __name__ == "__main__":
    start_time = None
    try:
        start_time = datetime.now()
        log.info("=" * 60)
        log.info("🚀 Запуск Telegram бота")
        log.info(f"   Время запуска: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Проверка конфигурации
        is_valid, error = bot_config.validate_config()
        if not is_valid:
            log.error(f"❌ {error}")
            log.error("\nПроверьте файл config/.env:")
            log.error("  - TG_API_TOKEN=ваш_токен")
            log.error("  - ID_TG=ваш_user_id")
            sys.exit(1)
        
        log.info("✅ Конфигурация проверена")
        log.info(f"   Разрешенных пользователей: {len(bot_config.TELEGRAM_ALLOWED_USERS)}")
        log.info("=" * 60)
        
        # Запуск бота
        run_bot()
        
    except KeyboardInterrupt:
        if start_time:
            duration = (datetime.now() - start_time).total_seconds()
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            log.info("=" * 60)
            log.info(f"⏹️ Бот остановлен пользователем")
            log.info(f"   Время работы: {minutes}м {seconds}с")
            log.info("=" * 60)
        else:
            log.info("\n⚠️ Остановка бота...")
    except Exception as e:
        if start_time:
            duration = (datetime.now() - start_time).total_seconds()
            minutes = int(duration // 60)
            seconds = int(duration % 60)
            log.error("=" * 60)
            log.error(f"❌ Критическая ошибка (время работы: {minutes}м {seconds}с): {e}")
            import traceback
            log.error(traceback.format_exc())
            log.error("=" * 60)
        else:
            log.error(f"❌ Критическая ошибка: {e}")
            import traceback
            log.error(traceback.format_exc())
        sys.exit(1)

