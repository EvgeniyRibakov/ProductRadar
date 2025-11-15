"""
Тестовый скрипт для проверки подключения к Google Sheets
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent))

from src.sheets_writer import SheetsWriter
from src import config
from src import logger

log = logger.get_logger("TestGoogleSheets")


def test_connection():
    """Тестирование подключения к Google Sheets"""
    
    log.info("=" * 60)
    log.info("ТЕСТИРОВАНИЕ ПОДКЛЮЧЕНИЯ К GOOGLE SHEETS")
    log.info("=" * 60)
    
    # Проверка credentials файла
    credentials_path = config.get_google_credentials_path()
    log.info(f"\n1. Проверка credentials файла...")
    if not credentials_path.exists():
        log.error(f"❌ Файл credentials не найден: {credentials_path}")
        return False
    else:
        log.info(f"✅ Файл credentials найден: {credentials_path}")
    
    # Создание SheetsWriter
    log.info(f"\n2. Создание SheetsWriter...")
    try:
        sheets_writer = SheetsWriter()
        log.info("✅ Объект SheetsWriter создан")
    except Exception as e:
        log.error(f"❌ Ошибка при создании SheetsWriter: {e}")
        return False
    
    # Подключение
    log.info(f"\n3. Подключение к Google Sheets...")
    try:
        if sheets_writer.connect():
            log.info("✅ Подключение успешно")
            log.info(f"  → Worksheet открыт: {sheets_writer.worksheet is not None}")
            log.info(f"  → Success worksheet открыт: {sheets_writer.success_worksheet is not None}")
            
            if sheets_writer.worksheet:
                log.info(f"  → Название листа 'Черновик': {sheets_writer.worksheet.title}")
                # Получаем количество строк
                try:
                    all_values = sheets_writer.worksheet.get_all_values()
                    log.info(f"  → Всего строк в 'Черновик': {len(all_values)}")
                    if len(all_values) > 0:
                        log.info(f"  → Последняя строка с данными: {len(all_values)}")
                except Exception as e:
                    log.warning(f"  ⚠️ Не удалось получить данные: {e}")
            
            if sheets_writer.success_worksheet:
                log.info(f"  → Название листа 'Успешные': {sheets_writer.success_worksheet.title}")
            
            return True
        else:
            log.error("❌ Подключение не удалось")
            return False
    except Exception as e:
        log.error(f"❌ Ошибка при подключении: {e}")
        import traceback
        log.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    success = test_connection()
    if success:
        log.info("\n" + "=" * 60)
        log.info("✅ ТЕСТ ПРОЙДЕН УСПЕШНО")
        log.info("=" * 60)
    else:
        log.error("\n" + "=" * 60)
        log.error("❌ ТЕСТ НЕ ПРОЙДЕН")
        log.error("=" * 60)
        sys.exit(1)

