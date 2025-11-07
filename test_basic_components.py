#!/usr/bin/env python3
"""
Тест базовых компонентов (config, logger, validator)
"""

import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import config
from src import logger
from src import validator


def test_config():
    """Тест конфигурации"""
    print("=" * 50)
    print("Тест config.py")
    print("=" * 50)
    
    # Проверка путей
    print(f"✅ PROJECT_ROOT: {config.PROJECT_ROOT}")
    print(f"✅ CONFIG_DIR: {config.CONFIG_DIR}")
    print(f"✅ LOGS_DIR: {config.LOGS_DIR}")
    
    # Проверка настроек
    print(f"✅ Pipiads Email: {config.PIPIADS_EMAIL}")
    print(f"✅ Google Sheets ID: {config.GOOGLE_SHEETS_ID}")
    print(f"✅ Sheet Name: {config.GOOGLE_SHEETS_SHEET_NAME}")
    print(f"✅ Min Impressions: {config.MIN_IMPRESSIONS}")
    print(f"✅ Days Back: {config.DAYS_BACK}")
    
    # Валидация конфигурации
    is_valid, error = config.validate_config()
    if is_valid:
        print("✅ Конфигурация валидна")
    else:
        print(f"❌ Ошибка конфигурации: {error}")
    
    print()


def test_logger():
    """Тест логгера"""
    print("=" * 50)
    print("Тест logger.py")
    print("=" * 50)
    
    log = logger.setup_logger("TestLogger", "DEBUG")
    
    log.debug("Это DEBUG сообщение")
    log.info("Это INFO сообщение")
    log.warning("Это WARNING сообщение")
    log.error("Это ERROR сообщение")
    
    # Проверка файла лога
    log_files = list(config.LOGS_DIR.glob("*.log"))
    if log_files:
        print(f"✅ Файл лога создан: {log_files[-1]}")
    else:
        print("⚠️ Файл лога не найден (может быть создан позже)")
    
    print()


def test_validator():
    """Тест валидатора"""
    print("=" * 50)
    print("Тест validator.py")
    print("=" * 50)
    
    # Тест parse_video_date
    test_dates = [
        "Oct 27 2025",
        "Jan 1 2024",
        "Dec 31 2025",
        "N/A",
        "invalid date",
        "Oct 32 2025",  # Невалидная дата
    ]
    
    print("Тест parse_video_date():")
    for date_str in test_dates:
        parsed = validator.parse_video_date(date_str)
        status = "✅" if parsed else "❌"
        print(f"  {status} '{date_str}' -> {parsed}")
    
    # Тест is_date_within_days
    print("\nТест is_date_within_days():")
    from datetime import datetime, timedelta
    today = datetime.now()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    print(f"  ✅ Сегодня ({today.strftime('%Y-%m-%d')}) в пределах 7 дней: {validator.is_date_within_days(today, 7)}")
    print(f"  ✅ Неделю назад ({week_ago.strftime('%Y-%m-%d')}) в пределах 7 дней: {validator.is_date_within_days(week_ago, 7)}")
    print(f"  ❌ Месяц назад ({month_ago.strftime('%Y-%m-%d')}) в пределах 7 дней: {validator.is_date_within_days(month_ago, 7)}")
    
    # Тест parse_impressions
    print("\nТест parse_impressions():")
    test_impressions = [
        "15.1K",
        "101300",
        "15,100",
        "1.5M",
        "N/A",
        "invalid",
    ]
    
    for imp_str in test_impressions:
        parsed = validator.parse_impressions(imp_str)
        print(f"  '{imp_str}' -> {parsed}")
    
    # Тест validate_impressions
    print("\nТест validate_impressions():")
    print(f"  ✅ 50000 >= 50000: {validator.validate_impressions(50000)}")
    print(f"  ✅ 100000 >= 50000: {validator.validate_impressions(100000)}")
    print(f"  ❌ 10000 >= 50000: {validator.validate_impressions(10000)}")
    
    # Тест validate_url
    print("\nТест validate_url():")
    test_urls = [
        "https://www.pipiads.com/ru/tiktok-shop-product/123",
        "https://m.tiktok.com/v/123.html",
        "N/A",
        "invalid url",
    ]
    
    for url in test_urls:
        is_valid = validator.validate_url(url)
        status = "✅" if is_valid else "❌"
        print(f"  {status} '{url}'")
    
    # Тест format_audience
    print("\nТест format_audience():")
    print(f"  '{validator.format_audience('35-45', 'Android')}'")
    print(f"  '{validator.format_audience('35-45', None)}'")
    print(f"  '{validator.format_audience(None, 'Android')}'")
    print(f"  '{validator.format_audience('N/A', None)}'")
    
    print()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Тестирование базовых компонентов")
    print("=" * 50 + "\n")
    
    try:
        test_config()
        test_logger()
        test_validator()
        
        print("=" * 50)
        print("✅ ВСЕ ТЕСТЫ ЗАВЕРШЕНЫ")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




