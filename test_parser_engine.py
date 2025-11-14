"""
Тестовый скрипт для проверки Parser Engine
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent))

from src.browser_manager import BrowserManager
from src.parser_engine import ParserEngine, ProductData
from src.sheets_writer import SheetsWriter
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
            wait_until="domcontentloaded",
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
        
        # 6. Подключение к Google Sheets (до начала обработки товаров)
        log.info("\n6. Подключение к Google Sheets...")
        sheets_writer = None
        try:
            sheets_writer = SheetsWriter()
            if sheets_writer.connect():
                log.info("✅ Подключение к Google Sheets успешно")
            else:
                log.warning("⚠️ Не удалось подключиться к Google Sheets, продолжаем без записи")
        except Exception as e:
            log.warning(f"⚠️ Ошибка при подключении к Google Sheets: {e}, продолжаем без записи")
        
        # 7. Цикл обработки товаров с главной страницы
        log.info("\n" + "=" * 80)
        log.info("7. НАЧАЛО ОБРАБОТКИ ТОВАРОВ")
        log.info("=" * 80)
        
        # Настройки обработки
        MIN_PRODUCTS_TO_COLLECT = 25  # Целевое количество успешных товаров
        MAX_PRODUCTS_TO_CHECK = 50     # Максимум товаров для проверки (защита от бесконечного цикла)
        PRODUCTS_PER_PAGE = 20         # Количество товаров на странице
        
        successful_products = 0  # Счетчик успешно обработанных товаров
        checked_products = 0      # Счетчик проверенных товаров
        skipped_products = []     # Список пропущенных товаров
        banned_products = set()   # Ban-list: URL товаров, которые уже проверялись и не подошли
        
        # Главный цикл обработки
        while successful_products < MIN_PRODUCTS_TO_COLLECT and checked_products < MAX_PRODUCTS_TO_CHECK:
            
            # 7.1. Получение списка товаров с главной страницы (текущее состояние)
            log.info(f"\n{'='*80}")
            log.info(f"Получение товаров с главной страницы...")
            log.info(f"Прогресс: {successful_products}/{MIN_PRODUCTS_TO_COLLECT} товаров обработано, "
                    f"{checked_products}/{MAX_PRODUCTS_TO_CHECK} проверено")
            log.info(f"{'='*80}")
            
            try:
                products = await parser.get_products_from_search_page(count=PRODUCTS_PER_PAGE)
            except Exception as e:
                log.error(f"❌ Ошибка при получении товаров: {e}")
                break
            
            if not products:
                log.error("❌ Не удалось получить товары, завершаем")
                break
            
            log.info(f"✅ Получено {len(products)} товаров на текущей странице")
            
            # 7.2. Цикл по товарам на текущей странице
            for product_index, product in enumerate(products):
                
                # Проверка достижения целевого количества
                if successful_products >= MIN_PRODUCTS_TO_COLLECT:
                    log.info(f"\n🎯 Цель достигнута! Собрано {MIN_PRODUCTS_TO_COLLECT} товаров")
                    break
                
                # Проверка лимита проверенных товаров
                if checked_products >= MAX_PRODUCTS_TO_CHECK:
                    log.warning(f"\n⚠️ Достигнут лимит проверок ({MAX_PRODUCTS_TO_CHECK} товаров)")
                    break
                
                # ⚠️ ПРОВЕРКА BAN-LIST: пропускаем товары, которые уже проверялись
                product_url = product.get('url', '')
                if product_url in banned_products:
                    log.info(f"⏭️  Пропуск товара (уже проверен): {product_url}")
                    continue
                
                checked_products += 1
                
                # Логирование начала обработки товара
                log.info(f"\n{'='*80}")
                log.info(f"📦 ТОВАР {checked_products}/{MAX_PRODUCTS_TO_CHECK} "
                        f"(успешных: {successful_products}/{MIN_PRODUCTS_TO_COLLECT})")
                log.info(f"{'='*80}")
                log.info(f"Название: {product.get('name', 'N/A')[:70]}...")
                log.info(f"Категория: {product.get('category', 'N/A')}")
                log.info(f"URL: {product.get('url', 'N/A')}")
                
                try:
                    # 7.3. Обработка товара (клик по индексу, переход на страницу товара)
                    product_data = await parser.get_product_details_with_return(
                        product_index=product_index,
                        sheets_writer=sheets_writer
                    )
                    
                    # 7.4. Проверка результата
                    if product_data is None:
                        # Ошибка при обработке
                        log.error(f"❌ Ошибка при обработке товара")
                        
                        # Добавляем в ban-list
                        banned_products.add(product_url)
                        
                        skipped_products.append({
                            "name": product.get('name', 'N/A'),
                            "reason": "Ошибка при обработке",
                            "videos_found": 0
                        })
                        continue
                    
                    if isinstance(product_data, dict) and product_data.get("status") == "insufficient_videos":
                        # Недостаточно видео - пропускаем
                        log.warning(f"⏭️  ПРОПУСК: недостаточно видео")
                        log.warning(f"   Найдено: {product_data.get('videos_found', 0)} видео")
                        log.warning(f"   Нужно: {product_data.get('videos_required', 3)} видео")
                        
                        # Добавляем в ban-list
                        banned_products.add(product_url)
                        
                        skipped_products.append({
                            "name": product_data.get('product_name', product.get('name', 'N/A')),
                            "reason": product_data.get('reason', 'Недостаточно видео'),
                            "videos_found": product_data.get('videos_found', 0)
                        })
                        continue
                    
                    # 7.5. Успешная обработка товара
                    if hasattr(product_data, 'videos') and len(product_data.videos) >= 3:
                        successful_products += 1
                        log.info(f"\n✅ УСПЕХ! Товар обработан ({successful_products}/{MIN_PRODUCTS_TO_COLLECT})")
                        log.info(f"   Название: {product_data.product_name[:70]}...")
                        log.info(f"   Количество видео: {len(product_data.videos)}")
                        
                        # Краткий вывод данных видео
                        for i, video in enumerate(product_data.videos[:3], 1):
                            log.info(f"   Видео {i}: {video.get('impression', 0)} impressions, "
                                    f"{video.get('country', 'N/A')}, {video.get('audience_age', 'N/A')}")
                    else:
                        log.warning(f"⚠️ Товар обработан, но меньше 3 видео")
                        
                        # Добавляем в ban-list
                        banned_products.add(product_url)
                        
                        skipped_products.append({
                            "name": getattr(product_data, 'product_name', product.get('name', 'N/A')),
                            "reason": "Меньше 3 видео после обработки",
                            "videos_found": len(getattr(product_data, 'videos', []))
                        })
                
                except Exception as e:
                    log.error(f"❌ Ошибка при обработке товара: {e}")
                    import traceback
                    log.error(traceback.format_exc())
                    
                    # Добавляем в ban-list
                    banned_products.add(product_url)
                    
                    skipped_products.append({
                        "name": product.get('name', 'N/A'),
                        "reason": f"Исключение: {str(e)[:50]}",
                        "videos_found": 0
                    })
            
            # 7.6. Проверка условий выхода из главного цикла
            if successful_products >= MIN_PRODUCTS_TO_COLLECT:
                break
            
            if checked_products >= MAX_PRODUCTS_TO_CHECK:
                break
        
        # 8. Итоговый отчет
        log.info(f"\n{'='*80}")
        log.info("📊 ИТОГОВЫЙ ОТЧЕТ")
        log.info(f"{'='*80}")
        log.info(f"✅ Успешно обработано товаров: {successful_products}")
        log.info(f"⏭️  Пропущено товаров: {len(skipped_products)}")
        log.info(f"🔍 Всего проверено товаров: {checked_products}")
        log.info(f"🚫 Товаров в ban-list: {len(banned_products)}")
        log.info(f"{'='*80}")
        
        if skipped_products:
            log.info(f"\n⏭️  СПИСОК ПРОПУЩЕННЫХ ТОВАРОВ:")
            for i, skipped in enumerate(skipped_products, 1):
                log.info(f"   {i}. {skipped['name'][:60]}...")
                log.info(f"      Причина: {skipped['reason']}")
                log.info(f"      Видео найдено: {skipped['videos_found']}")
        
        if successful_products >= MIN_PRODUCTS_TO_COLLECT:
            log.info(f"\n🎉 ЦЕЛЬ ДОСТИГНУТА! Собрано {MIN_PRODUCTS_TO_COLLECT} товаров")
        elif checked_products >= MAX_PRODUCTS_TO_CHECK:
            log.warning(f"\n⚠️ Достигнут лимит проверок ({MAX_PRODUCTS_TO_CHECK} товаров)")
            log.warning(f"   Собрано только {successful_products} товаров из {MIN_PRODUCTS_TO_COLLECT}")
        
        # 9. Создание summary-файла итерации
        log.info("\n" + "=" * 60)
        log.info("📝 Создание summary-файла итерации...")
        log.info("=" * 60)
        try:
            from datetime import datetime
            import os
            
            summary_dir = "logs/summaries"
            os.makedirs(summary_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            summary_file = f"{summary_dir}/iteration_{timestamp}.md"
            
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(f"# 📊 Итерация тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("## ✅ Результаты\n\n")
                f.write(f"- **Успешно обработано:** {successful_products} товаров\n")
                f.write(f"- **Пропущено:** {len(skipped_products)} товаров\n")
                f.write(f"- **Проверено:** {checked_products} товаров\n")
                f.write(f"- **Ban-list:** {len(banned_products)} товаров\n\n")
                
                if successful_products > 0:
                    f.write("### 🎉 SUCCESS\n\n")
                    f.write(f"✅ Обработано {successful_products} товаров с >= 3 видео\n\n")
                
                if skipped_products:
                    f.write("### ⏭️ ПРОПУЩЕННЫЕ ТОВАРЫ\n\n")
                    for i, skipped in enumerate(skipped_products, 1):
                        f.write(f"{i}. **{skipped['name'][:60]}...**\n")
                        f.write(f"   - Причина: {skipped['reason']}\n")
                        f.write(f"   - Видео найдено: {skipped['videos_found']}\n\n")
                
                f.write("## 🔍 Технические детали\n\n")
                f.write(f"- **Целевое количество:** {MIN_PRODUCTS_TO_COLLECT} товаров\n")
                f.write(f"- **Лимит проверок:** {MAX_PRODUCTS_TO_CHECK} товаров\n")
                f.write(f"- **Критерии видео:** >= 5K impressions, <= 30 дней\n\n")
                
                if successful_products >= MIN_PRODUCTS_TO_COLLECT:
                    f.write("## 🎯 Статус: ЦЕЛЬ ДОСТИГНУТА ✅\n\n")
                elif checked_products >= MAX_PRODUCTS_TO_CHECK:
                    f.write("## ⚠️ Статус: Достигнут лимит проверок\n\n")
                else:
                    f.write("## ❌ Статус: Прервано\n\n")
            
            log.info(f"✅ Summary сохранен: {summary_file}")
        except Exception as e:
            log.error(f"❌ Ошибка при создании summary: {e}")
        
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

