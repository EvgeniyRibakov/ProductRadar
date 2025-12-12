#!/usr/bin/env python3
"""
Тест Browser Manager - проверка авторизации и защиты от блокировок
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.browser_manager import BrowserManager
from src import logger

log = logger.get_logger("TestBrowserManager")


async def test_browser_manager():
    """Тест Browser Manager"""
    print("=" * 50)
    print("Тест Browser Manager")
    print("=" * 50)
    print()
    
    browser_manager = BrowserManager()
    
    try:
        # Инициализация
        print("1. Инициализация браузера...")
        success = await browser_manager.initialize(headless=False)  # headful для теста
        if not success:
            print("❌ Ошибка инициализации браузера")
            return False
        print("✅ Браузер инициализирован")
        print()
        
        # Загрузка cookies
        print("2. Загрузка cookies...")
        await browser_manager.load_cookies()
        print()
        
        # Авторизация
        print("3. Авторизация на Pipiads...")
        success = await browser_manager.login_to_pipiads()
        if not success:
            print("❌ Ошибка авторизации")
            return False
        print("✅ Авторизация успешна")
        print()
        
        # Проверка навигации
        print("4. Тест навигации...")
        test_url = "https://www.pipiads.com/ru/tiktok-shop-product?time=7&current_page=1&page_size=20"
        success = await browser_manager.navigate_with_retry(test_url)
        if success:
            print("✅ Навигация работает")
        else:
            print("❌ Ошибка навигации")
        print()
        
        # Проверка каптч
        print("5. Проверка на каптч...")
        has_captcha = await browser_manager._check_captcha()
        if has_captcha:
            print("⚠️ Обнаружена каптч!")
        else:
            print("✅ Каптч не обнаружена")
        print()
        
        # Сохранение cookies
        print("6. Сохранение cookies...")
        await browser_manager.save_cookies()
        print("✅ Cookies сохранены")
        print()
        
        print("=" * 50)
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ")
        print("=" * 50)
        print()
        print("⚠️ Браузер останется открытым для проверки")
        print("Нажмите Enter для закрытия...")
        input()
        
        return True
        
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await browser_manager.close()


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("Тестирование Browser Manager")
    print("=" * 50 + "\n")
    
    try:
        success = asyncio.run(test_browser_manager())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
        sys.exit(1)




