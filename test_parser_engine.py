"""
Тестовый скрипт для проверки Parser Engine
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent))

from src.browser_manager import BrowserManager
from src.parser_engine import ParserEngine
from src import config
from src import logger

log = logger.get_logger("TestParserEngine")


async def test_parser_engine():
    """Тестирование Parser Engine"""
    
    browser_manager = None
    try:
        log.info("=" * 60)
        log.info("ТЕСТИРОВАНИЕ PARSER ENGINE")
        log.info("=" * 60)
        
        # 1. Инициализация браузера
        log.info("\n1. Инициализация браузера...")
        browser_manager = BrowserManager()
        success = await browser_manager.initialize(headless=False)  # headful для отладки
        if not success:
            log.error("❌ Не удалось инициализировать браузер")
            return
        
        # 2. Загрузка cookies (если есть)
        log.info("\n2. Загрузка cookies...")
        await browser_manager.load_cookies()
        
        # 3. Переход на начальную страницу Pipiads
        log.info("\n3. Переход на страницу Pipiads...")
        success = await browser_manager.navigate_with_retry(
            config.PIPIADS_INITIAL_URL,
            wait_until="networkidle",
            timeout=30000
        )
        if not success:
            log.error("❌ Не удалось загрузить страницу")
            return
        
        await browser_manager.human_delay(2, 3)
        
        # 4. Авторизация (если нужно)
        log.info("\n4. Проверка авторизации...")
        is_logged_in = await browser_manager._check_logged_in_strict()
        if not is_logged_in:
            log.info("Требуется авторизация...")
            success = await browser_manager.login_to_pipiads()
            if not success:
                log.error("❌ Не удалось авторизоваться")
                return
            await browser_manager.save_cookies()
        else:
            log.info("✅ Уже авторизован")
        
        # 5. Создание Parser Engine
        log.info("\n5. Создание Parser Engine...")
        parser = ParserEngine(browser_manager.page)
        parser.set_browser_manager(browser_manager)
        
        # 6. Тест: получение товаров со страницы поиска (для MVP-0: 1 товар)
        log.info("\n6. Тест: получение товаров со страницы поиска...")
        products = await parser.get_products_from_search_page(count=1)  # MVP-0: только 1 товар
        
        if not products:
            log.error("❌ Не удалось получить товары")
            return
        
        log.info(f"✅ Получено {len(products)} товаров:")
        for i, product in enumerate(products, 1):
            log.info(f"  {i}. {product.get('name', 'N/A')[:50]}...")
            log.info(f"     Категория: {product.get('category', 'N/A')}")
            log.info(f"     URL: {product.get('url', 'N/A')}")
        
        # 7. Тест: получение деталей первого товара
        if products:
            first_product = products[0]
            log.info(f"\n7. Тест: получение деталей товара '{first_product.get('name', 'N/A')[:50]}...'")
            
            try:
                product_data = await parser.get_product_details(first_product['url'])
                
                log.info(f"\n✅ Данные товара:")
                log.info(f"  Название: {product_data.product_name}")
                log.info(f"  Категория: {product_data.category}")
                log.info(f"  Pipiads ссылка: {product_data.pipiads_link}")
                log.info(f"  Количество видео: {len(product_data.videos)}")
                
                # 8. Вывод данных видео
                if product_data.videos:
                    log.info(f"\n8. Данные видео:")
                    for i, video in enumerate(product_data.videos, 1):
                        log.info(f"\n  Видео {i}:")
                        log.info(f"    TikTok ссылка: {video.get('tiktok_link', 'N/A')}")
                        log.info(f"    Impressions: {video.get('impression', 0)}")
                        log.info(f"    Script: {video.get('script', 'N/A')[:100]}...")
                        log.info(f"    Hook: {video.get('hook', 'N/A')[:100]}...")
                        log.info(f"    Audience: {video.get('audience_age', 'N/A')}")
                        log.info(f"    Country: {video.get('country', 'N/A')}")
                        log.info(f"    First seen: {video.get('first_seen', 'N/A')}")
                else:
                    log.warning("⚠️ Видео не найдены")
            except Exception as e:
                log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА при получении деталей товара: {e}")
                import traceback
                log.error(traceback.format_exc())
                # Сохраняем скриншот
                if browser_manager and browser_manager.page:
                    try:
                        screenshot_path = config.SCREENSHOTS_DIR / f"critical_error_{int(asyncio.get_event_loop().time())}.png"
                        await browser_manager.page.screenshot(path=str(screenshot_path), full_page=True)
                        log.info(f"📸 Скриншот сохранен: {screenshot_path}")
                    except:
                        pass
        
        log.info("\n" + "=" * 60)
        log.info("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")
        log.info("=" * 60)
        
        # Задержка перед закрытием (для просмотра результата)
        log.info("\n⏸️ Ожидание 10 секунд перед закрытием браузера (для просмотра результата)...")
        log.info("   Нажмите Ctrl+C, если хотите закрыть раньше")
        try:
            await asyncio.sleep(10)
        except KeyboardInterrupt:
            log.info("   Прервано пользователем")
        
    except KeyboardInterrupt:
        log.warning("\n⚠️ Прервано пользователем (Ctrl+C)")
    except Exception as e:
        log.error(f"\n{'='*60}")
        log.error(f"❌ КРИТИЧЕСКАЯ ОШИБКА при тестировании: {e}")
        log.error(f"{'='*60}")
        import traceback
        log.error("Полная трассировка:")
        log.error(traceback.format_exc())
        
        # Сохраняем скриншот при ошибке
        if browser_manager and browser_manager.page:
            try:
                screenshot_path = config.SCREENSHOTS_DIR / f"error_test_{int(asyncio.get_event_loop().time())}.png"
                await browser_manager.page.screenshot(path=str(screenshot_path), full_page=True)
                log.info(f"📸 Скриншот сохранен: {screenshot_path}")
            except Exception as e2:
                log.error(f"Не удалось сохранить скриншот: {e2}")
        
        log.error("\n⚠️ Браузер останется открытым для отладки на 30 секунд...")
        try:
            await asyncio.sleep(30)
        except:
            pass
    
    finally:
        if browser_manager:
            await browser_manager.close()


if __name__ == "__main__":
    asyncio.run(test_parser_engine())

