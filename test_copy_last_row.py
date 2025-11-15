"""
Тестовый скрипт для копирования последней строки из "Черновик" в "Успешные"
"""

import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent))

from src.sheets_writer import SheetsWriter
from src import config
from src import logger

log = logger.get_logger("TestCopyLastRow")


def test_copy_last_row():
    """Тестирование копирования последней строки"""
    
    log.info("=" * 60)
    log.info("ТЕСТИРОВАНИЕ КОПИРОВАНИЯ ПОСЛЕДНЕЙ СТРОКИ")
    log.info("=" * 60)
    
    # Создание SheetsWriter
    log.info(f"\n1. Создание SheetsWriter...")
    try:
        sheets_writer = SheetsWriter()
        log.info("✅ Объект SheetsWriter создан")
    except Exception as e:
        log.error(f"❌ Ошибка при создании SheetsWriter: {e}")
        return False
    
    # Подключение
    log.info(f"\n2. Подключение к Google Sheets...")
    if not sheets_writer.connect():
        log.error("❌ Не удалось подключиться к Google Sheets")
        return False
    log.info("✅ Подключение успешно")
    
    # Получение последней строки
    log.info(f"\n3. Получение последней строки с данными...")
    last_row = sheets_writer.get_last_row_with_data()
    
    if last_row == 0:
        log.warning("⚠️ В листе 'Черновик' нет данных для копирования")
        return False
    
    log.info(f"✅ Последняя строка: {last_row}")
    
    # Копирование
    log.info(f"\n4. Копирование последней строки в 'Успешные'...")
    if sheets_writer.copy_last_row_to_success():
        log.info("✅ Копирование успешно")
        return True
    else:
        log.error("❌ Копирование не удалось")
        return False


if __name__ == "__main__":
    success = test_copy_last_row()
    if success:
        log.info("\n" + "=" * 60)
        log.info("✅ ТЕСТ ПРОЙДЕН УСПЕШНО")
        log.info("=" * 60)
    else:
        log.error("\n" + "=" * 60)
        log.error("❌ ТЕСТ НЕ ПРОЙДЕН")
        log.error("=" * 60)
        sys.exit(1)

