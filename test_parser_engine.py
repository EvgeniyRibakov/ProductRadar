"""
Тестовый скрипт для проверки Parser Engine
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем путь к src
sys.path.insert(0, str(Path(__file__).parent))

from src.browser_manager import BrowserManager
from src.parser_engine import ParserEngine, ProductData
from src.sheets_writer import SheetsWriter
from src import config
from src import logger

log = logger.get_logger("TestParserEngine")

# Проверка наличия credentials файла перед началом
credentials_path = config.get_google_credentials_path()
if not credentials_path.exists():
    log.warning(f"⚠️ Файл Google credentials не найден: {credentials_path}")
    log.warning("  → Запись в Google Sheets будет недоступна")
else:
    log.info(f"✅ Файл Google credentials найден: {credentials_path}")


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
        # Используем настройку из переменной окружения (для Telegram бота)
        headless_mode = os.environ.get("BROWSER_HEADLESS", "false").lower() == "true"
        log.info(f"  → Режим браузера: {'headless' if headless_mode else 'headful'}")
        success = await browser_manager.initialize(headless=headless_mode)
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
            log.info("  → Создан объект SheetsWriter")
            if sheets_writer.connect():
                log.info("✅ Подключение к Google Sheets успешно")
                log.info(f"  → Worksheet открыт: {sheets_writer.worksheet is not None}")
            else:
                log.warning("⚠️ Не удалось подключиться к Google Sheets, продолжаем без записи")
                log.warning("  → sheets_writer будет None, запись в таблицу не будет работать")
                sheets_writer = None  # Явно устанавливаем None при неудаче
        except Exception as e:
            log.error(f"❌ Критическая ошибка при подключении к Google Sheets: {e}")
            import traceback
            log.error(traceback.format_exc())
            log.warning("  → sheets_writer будет None, запись в таблицу не будет работать")
            sheets_writer = None  # Явно устанавливаем None при ошибке
        
        # 7. Цикл обработки товаров с главной страницы
        log.info("\n" + "=" * 80)
        log.info("7. НАЧАЛО ОБРАБОТКИ ТОВАРОВ")
        log.info("=" * 80)
        
        # Настройки обработки
        # Можно переопределить через переменные окружения (для Telegram бота)
        MIN_PRODUCTS_TO_COLLECT = int(os.getenv("MIN_PRODUCTS", "3"))
        MAX_PRODUCTS_TO_CHECK = int(os.getenv("MAX_PRODUCTS_TO_CHECK", "40"))
        PRODUCTS_PER_PAGE = int(os.getenv("PRODUCTS_PER_PAGE", "20"))
        MIN_IMPRESSIONS = int(os.getenv("MIN_IMPRESSIONS", "1000"))
        DAYS_BACK = int(os.getenv("DAYS_BACK", "60"))
        
        log.info(f"\n📋 Настройки парсера:")
        log.info(f"   MIN_PRODUCTS_TO_COLLECT: {MIN_PRODUCTS_TO_COLLECT}")
        log.info(f"   MAX_PRODUCTS_TO_CHECK: {MAX_PRODUCTS_TO_CHECK}")
        log.info(f"   PRODUCTS_PER_PAGE: {PRODUCTS_PER_PAGE}")
        log.info(f"   MIN_IMPRESSIONS: {MIN_IMPRESSIONS}")
        log.info(f"   DAYS_BACK: {DAYS_BACK}")
        
        successful_products = 0  # Счетчик успешно обработанных товаров
        checked_products = 0      # Счетчик проверенных товаров
        skipped_products = []     # Список пропущенных товаров
        banned_products = set()   # Ban-list: URL товаров, которые уже обрабатывались (нормализованные)
        all_products_analytics = []  # Аналитика ВСЕХ товаров для summary-файла
        
        def normalize_url(url: str) -> str:
            """Нормализовать URL (убрать слэш в конце, привести к единому виду)"""
            if not url:
                return ""
            url = url.strip().rstrip('/')
            # Убираем параметры запроса если есть
            if '?' in url:
                url = url.split('?')[0]
            return url
        
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
            
            # 7.1.5. Дедупликация по URL (простая и надежная)
            # ВАЖНО: Используем banned_products для проверки, чтобы не обрабатывать товары, которые уже были обработаны
            unique_products = []
            duplicate_count = 0
            seen_urls = set()  # Для дедупликации внутри текущего списка
            
            for product in products:
                product_url = normalize_url(product.get('url', ''))
                
                if not product_url:
                    log.warning(f"⚠️ Пропуск товара без URL")
                    continue
                
                # Проверяем против banned_products (уже обработанные товары)
                if product_url in banned_products:
                    duplicate_count += 1
                    log.info(f"⏭️  Дубликат товара пропущен (уже в ban-list): {product_url}")
                    continue
                
                # Проверяем на дубликаты внутри текущего списка
                if product_url in seen_urls:
                    duplicate_count += 1
                    log.info(f"⏭️  Дубликат товара пропущен (в текущем списке): {product_url}")
                    continue
                
                seen_urls.add(product_url)
                # Обновляем URL в словаре товара на нормализованный
                product['url'] = product_url
                unique_products.append(product)
            
            if duplicate_count > 0:
                log.info(f"🔍 Найдено {duplicate_count} дубликатов, оставлено {len(unique_products)} уникальных товаров")
            
            products = unique_products  # Используем только уникальные товары
            log.info(f"✅ После дедупликации: {len(products)} уникальных товаров для обработки")
            
            # 7.2. Цикл по товарам на текущей странице
            for product_index, product in enumerate(products):
                
                # Проверка лимита проверенных товаров (приоритет над целью)
                if checked_products >= MAX_PRODUCTS_TO_CHECK:
                    log.warning(f"\n⚠️ Достигнут лимит проверок ({MAX_PRODUCTS_TO_CHECK} товаров)")
                    break
                
                # Информация о достижении цели (но продолжаем работу до лимита)
                if successful_products >= MIN_PRODUCTS_TO_COLLECT and successful_products == MIN_PRODUCTS_TO_COLLECT:
                    log.info(f"\n🎯 Цель достигнута! Собрано {MIN_PRODUCTS_TO_COLLECT} товаров (продолжаем до лимита проверок)")
                
                # ⚠️ ПРОВЕРКА BAN-LIST: пропускаем товары, которые уже обрабатывались
                product_url = normalize_url(product.get('url', ''))
                
                if not product_url:
                    log.warning(f"⚠️ Не удалось нормализовать URL товара, пропускаем")
                    continue
                
                # КРИТИЧНО: Проверяем ban-list ПЕРЕД обработкой
                if product_url in banned_products:
                    log.warning(f"🚫 ПРОПУСК: Товар уже в ban-list: {product_url}")
                    log.warning(f"   Это дубликат! Пропускаем обработку.")
                    continue
                
                checked_products += 1
                
                # Логирование начала обработки товара
                log.info(f"\n{'='*80}")
                log.info(f"📦 ТОВАР {checked_products}/{MAX_PRODUCTS_TO_CHECK} "
                        f"(успешных: {successful_products}/{MIN_PRODUCTS_TO_COLLECT})")
                log.info(f"{'='*80}")
                log.info(f"Название: {product.get('name', 'N/A')[:70]}...")
                log.info(f"Категория: {product.get('category', 'N/A')}")
                log.info(f"URL: {product_url}")
                
                try:
                    # 7.3. Обработка товара (переход на страницу товара по URL)
                    # ВАЖНО: Передаем banned_products для дополнительной проверки дубликатов
                    product_data = await parser.get_product_details_with_return(
                        product_url=product_url,
                        sheets_writer=sheets_writer,
                        banned_products=banned_products
                    )
                    
                    # КРИТИЧНО: Добавляем товар в ban-list ПОСЛЕ обработки (независимо от результата)
                    banned_products.add(product_url)
                    log.info(f"   ✅ Добавлен в ban-list ПОСЛЕ обработки: {product_url}")
                    
                    # 7.4. Проверка результата
                    if product_data is None:
                        # Ошибка при обработке
                        log.error(f"❌ Ошибка при обработке товара")
                        
                        skipped_products.append({
                            "name": product.get('name', 'N/A'),
                            "url": product_url,
                            "reason": "Ошибка при обработке",
                            "videos_found": 0
                        })
                        
                        # Добавляем в аналитику (без данных о видео)
                        all_products_analytics.append({
                            "product_name": product.get('name', 'N/A'),
                            "product_url": product_url,
                            "category": product.get('category', 'N/A'),
                            "success": False,
                            "videos_found": 0,
                            "top_3_videos": []
                        })
                        continue
                    
                    # Проверка на дубликат (если вернулся статус "duplicate")
                    if isinstance(product_data, dict) and product_data.get("status") == "duplicate":
                        duplicate_url = product_data.get('product_url', 'N/A')
                        log.warning(f"🚫 ПРОПУСК: Товар уже обработан (дубликат): {duplicate_url}")
                        duplicate_count += 1
                        continue
                    
                    if isinstance(product_data, dict) and product_data.get("status") == "insufficient_videos":
                        # Недостаточно видео - пропускаем
                        log.warning(f"⏭️  ПРОПУСК: недостаточно видео")
                        log.warning(f"   Найдено: {product_data.get('videos_found', 0)} видео")
                        log.warning(f"   Нужно: {product_data.get('videos_required', 3)} видео")
                        
                        skipped_products.append({
                            "name": product_data.get('product_name', product.get('name', 'N/A')),
                            "url": product_url,
                            "reason": product_data.get('reason', 'Недостаточно видео'),
                            "videos_found": product_data.get('videos_found', 0)
                        })
                        
                        # Добавляем в аналитику (без данных о видео - товар вернул insufficient_videos)
                        all_products_analytics.append({
                            "product_name": product_data.get('product_name', product.get('name', 'N/A')),
                            "product_url": product_url,
                            "category": product_data.get('category', product.get('category', 'N/A')),
                            "success": False,
                            "videos_found": product_data.get('videos_found', 0),
                            "top_3_videos": []  # Нет данных о топ-3
                        })
                        continue
                    
                    # 7.5. Сбор аналитики для summary
                    analytics_entry = {
                        "product_name": getattr(product_data, 'product_name', 'N/A'),
                        "product_url": getattr(product_data, 'pipiads_link', product_url),
                        "category": getattr(product_data, 'category', 'N/A'),
                        "success": False,
                        "videos_found": len(getattr(product_data, 'videos', [])),
                        "top_3_videos": []
                    }
                    
                    # Извлекаем ТОП-3 видео (по impression) из ВСЕХ видео с полными данными
                    if hasattr(product_data, '_all_videos_raw'):
                        all_videos = product_data._all_videos_raw
                        # Сортируем по impression (desc) и берем топ-3
                        sorted_videos = sorted(all_videos, key=lambda v: v.get('impression', 0) if isinstance(v.get('impression'), (int, float)) else 0, reverse=True)
                        for i, video in enumerate(sorted_videos[:3], 1):
                            analytics_entry["top_3_videos"].append({
                                "rank": i,
                                "impression": video.get('impression', 0),
                                "first_seen": video.get('first_seen', 'N/A'),
                                "ad_search_url": video.get('ad_search_url', 'N/A'),
                                "tiktok_link": video.get('tiktok_link', 'N/A'),
                                "script": video.get('script', 'N/A'),
                                "hook": video.get('hook', 'N/A'),
                                "country": video.get('country', 'N/A'),
                                "audience_age": video.get('audience_age', 'N/A')
                            })
                    
                    # Также добавляем данные из финальных видео (если они есть и более полные)
                    if hasattr(product_data, 'videos') and product_data.videos:
                        for i, final_video in enumerate(product_data.videos[:3], 1):
                            # Обновляем данные, если они более полные
                            if i <= len(analytics_entry["top_3_videos"]):
                                top_video = analytics_entry["top_3_videos"][i-1]
                                # Обновляем только если данных больше
                                if final_video.get('tiktok_link') and final_video.get('tiktok_link') != 'N/A':
                                    top_video['tiktok_link'] = final_video.get('tiktok_link', top_video.get('tiktok_link', 'N/A'))
                                if final_video.get('script') and final_video.get('script') != 'N/A':
                                    top_video['script'] = final_video.get('script', top_video.get('script', 'N/A'))
                                if final_video.get('hook') and final_video.get('hook') != 'N/A':
                                    top_video['hook'] = final_video.get('hook', top_video.get('hook', 'N/A'))
                                if final_video.get('country') and final_video.get('country') != 'N/A':
                                    top_video['country'] = final_video.get('country', top_video.get('country', 'N/A'))
                                if final_video.get('audience_age') and final_video.get('audience_age') != 'N/A':
                                    top_video['audience_age'] = final_video.get('audience_age', top_video.get('audience_age', 'N/A'))
                    
                    # 7.6. Успешная обработка товара
                    if hasattr(product_data, 'videos') and len(product_data.videos) >= 3:
                        successful_products += 1
                        analytics_entry["success"] = True
                        
                        log.info(f"\n✅ УСПЕХ! Товар обработан ({successful_products}/{MIN_PRODUCTS_TO_COLLECT})")
                        log.info(f"   Название: {product_data.product_name[:70]}...")
                        log.info(f"   Количество видео: {len(product_data.videos)}")
                        
                        # Краткий вывод данных видео
                        for i, video in enumerate(product_data.videos[:3], 1):
                            log.info(f"   Видео {i}: {video.get('impression', 0)} impressions, "
                                    f"{video.get('country', 'N/A')}, {video.get('audience_age', 'N/A')}")
                        
                        # Проверяем заполненность строки и копируем в "Успешные" если все поля заполнены
                        if sheets_writer and hasattr(product_data, '_sheets_row'):
                            try:
                                # Проверяем, что все столбцы A-Z (кроме C) заполнены
                                if sheets_writer.is_row_complete(product_data._sheets_row):
                                    sheets_writer.copy_to_success_sheet(product_data._sheets_row)
                                    log.info(f"  ✅ Строка {product_data._sheets_row} полностью заполнена → скопирована в 'Успешные'")
                                else:
                                    log.warning(f"  ⚠️ Строка {product_data._sheets_row} не полностью заполнена (есть пустые ячейки)")
                            except Exception as e:
                                log.warning(f"  ⚠️ Не удалось обработать копирование в 'Успешные': {e}")
                    
                    # Добавляем в аналитику
                    all_products_analytics.append(analytics_entry)
                    
                    # 7.7. Если видео меньше 3 - пропускаем
                    if not analytics_entry["success"]:
                        log.warning(f"⚠️ Товар обработан, но меньше 3 видео")
                        
                        skipped_products.append({
                            "name": getattr(product_data, 'product_name', product.get('name', 'N/A')),
                            "url": product_url,
                            "reason": "Меньше 3 видео после обработки",
                            "videos_found": len(getattr(product_data, 'videos', []))
                        })
                
                except Exception as e:
                    log.error(f"❌ Ошибка при обработке товара: {e}")
                    import traceback
                    log.error(traceback.format_exc())
                    
                    # Добавляем в ban-list даже при ошибке, чтобы не обрабатывать повторно
                    banned_products.add(product_url)
                    log.info(f"   ✅ Добавлен в ban-list после ошибки: {product_url}")
                    
                    skipped_products.append({
                        "name": product.get('name', 'N/A'),
                        "url": product_url,
                        "reason": f"Исключение: {str(e)[:50]}",
                        "videos_found": 0
                    })
            
            # 7.6. Проверка условий выхода из главного цикла
            # Останавливаемся только при достижении лимита проверок
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
        
        # Вывод ban-list
        if banned_products:
            log.info(f"\n🚫 BAN-LIST (обработанные товары):")
            for i, product_url in enumerate(sorted(banned_products), 1):
                log.info(f"   {i}. {product_url}")
        
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
        
        # 9. Создание summary-файла итерации с подробной аналитикой
        log.info("\n" + "=" * 60)
        log.info("📝 Создание summary-файла итерации с аналитикой видео...")
        log.info("=" * 60)
        try:
            from datetime import datetime
            
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
                
                # ═══════════════════════════════════════════════════════
                # НОВЫЙ БЛОК: Подробная аналитика ТОП-3 видео по товарам
                # ═══════════════════════════════════════════════════════
                if all_products_analytics:
                    f.write("---\n\n")
                    f.write("## 📦 Обработанные товары\n\n")
                    f.write(f"**Критерии фильтрации:** >= {config.MIN_IMPRESSIONS} impressions, возраст <= {config.DAYS_BACK} дней\n\n")
                    
                    for idx, product in enumerate(all_products_analytics, 1):
                        status_icon = "✅" if product["success"] else "❌"
                        product_name = product.get('product_name', 'N/A')
                        product_url = product.get('product_url', 'N/A')
                        category = product.get('category', 'N/A')
                        
                        f.write(f"### {status_icon} Товар #{idx}\n\n")
                        f.write(f"- **Название:** {product_name}\n")
                        f.write(f"- **Категория:** {category}\n")
                        f.write(f"- **Ссылка:** [{product_url}]({product_url})\n")
                        f.write(f"- **Статус:** {'✅ УСПЕХ (>= 3 видео)' if product['success'] else '❌ ПРОПУЩЕН (< 3 видео)'}\n")
                        f.write(f"- **Найдено подходящих видео:** {product['videos_found']}\n\n")
                        
                        # Решение: почему принят или пропущен
                        if product['success']:
                            f.write("**Решение:** Товар принят - найдено >= 3 подходящих видео после фильтрации\n\n")
                        else:
                            reason = "Недостаточно подходящих видео после фильтрации"
                            if product['videos_found'] == 0:
                                reason = "Не найдено подходящих видео (все отфильтрованы по критериям)"
                            f.write(f"**Решение:** Товар пропущен - {reason}\n\n")
                        
                        # ТОП-3 видео с полными артефактами
                        if product['top_3_videos']:
                            f.write("#### 🏆 ТОП-3 видео по impression:\n\n")
                            for video in product['top_3_videos']:
                                impression = video.get('impression', 0)
                                first_seen = video.get('first_seen', 'N/A')
                                ad_url = video.get('ad_search_url', 'N/A')
                                tiktok_link = video.get('tiktok_link', 'N/A')
                                script = video.get('script', 'N/A')
                                hook = video.get('hook', 'N/A')
                                country = video.get('country', 'N/A')
                                audience_age = video.get('audience_age', 'N/A')
                                
                                # Проверка на соответствие критериям
                                meets_criteria = impression >= config.MIN_IMPRESSIONS
                                criteria_icon = "✅" if meets_criteria else "⚠️"
                                
                                f.write(f"{video['rank']}. {criteria_icon} **{impression:,} impressions** | First seen: {first_seen}\n")
                                
                                # Артефакты
                                if ad_url and ad_url != 'N/A':
                                    f.write(f"   - **Ad-search URL:** [{ad_url}]({ad_url})\n")
                                if tiktok_link and tiktok_link != 'N/A':
                                    f.write(f"   - **TikTok ссылка:** [{tiktok_link}]({tiktok_link})\n")
                                if country and country != 'N/A':
                                    f.write(f"   - **Страна:** {country}\n")
                                if audience_age and audience_age != 'N/A':
                                    f.write(f"   - **Аудитория:** {audience_age}\n")
                                if script and script != 'N/A' and len(script) > 0:
                                    script_preview = script[:100] + "..." if len(script) > 100 else script
                                    f.write(f"   - **Script:** {script_preview}\n")
                                if hook and hook != 'N/A' and len(hook) > 0:
                                    hook_preview = hook[:100] + "..." if len(hook) > 100 else hook
                                    f.write(f"   - **Hook:** {hook_preview}\n")
                                f.write("\n")
                        else:
                            f.write("   ⚠️ Нет данных о видео (возможно, ошибка парсинга)\n\n")
                        
                        f.write("---\n\n")
                
                # Пропущенные товары с подробностями
                if skipped_products:
                    f.write("## ⏭️ Пропущенные товары\n\n")
                    f.write("**Причины пропуска:**\n\n")
                    for i, skipped in enumerate(skipped_products, 1):
                        f.write(f"### {i}. {skipped['name']}\n\n")
                        f.write(f"- **Причина пропуска:** {skipped['reason']}\n")
                        f.write(f"- **Найдено видео:** {skipped['videos_found']}\n")
                        if 'url' in skipped:
                            f.write(f"- **Ссылка:** [{skipped['url']}]({skipped['url']})\n")
                        f.write("\n")
                
                # Ban-list
                if banned_products:
                    f.write("### 🚫 Ban-list (обработанные товары)\n\n")
                    for i, product_url in enumerate(sorted(banned_products), 1):
                        f.write(f"{i}. `{product_url}`\n")
                    f.write("\n")
                
                f.write("## 🔍 Технические детали итерации\n\n")
                f.write(f"- **Целевое количество:** {MIN_PRODUCTS_TO_COLLECT} товаров\n")
                f.write(f"- **Лимит проверок:** {MAX_PRODUCTS_TO_CHECK} товаров\n")
                f.write(f"- **Критерии фильтрации видео:**\n")
                f.write(f"  - Минимум impressions: >= {config.MIN_IMPRESSIONS:,}\n")
                f.write(f"  - Максимальный возраст: <= {config.DAYS_BACK} дней\n")
                f.write(f"- **Приоритет impressions:** >= {config.PRIORITY_IMPRESSIONS:,}\n\n")
                
                # Статистика по страницам (если есть информация)
                f.write("## 📊 Статистика обработки\n\n")
                f.write(f"- **Всего проверено товаров:** {checked_products}\n")
                f.write(f"- **Успешно обработано:** {successful_products}\n")
                f.write(f"- **Пропущено:** {len(skipped_products)}\n")
                f.write(f"- **В ban-list:** {len(banned_products)}\n")
                if successful_products > 0:
                    success_rate = (successful_products / checked_products * 100) if checked_products > 0 else 0
                    f.write(f"- **Процент успеха:** {success_rate:.1f}%\n")
                f.write("\n")
                
                if successful_products >= MIN_PRODUCTS_TO_COLLECT:
                    f.write("## 🎯 Статус: ЦЕЛЬ ДОСТИГНУТА ✅\n\n")
                elif checked_products >= MAX_PRODUCTS_TO_CHECK:
                    f.write("## ⚠️ Статус: Достигнут лимит проверок\n\n")
                else:
                    f.write("## ❌ Статус: Прервано\n\n")
            
            log.info(f"✅ Summary с аналитикой сохранен: {summary_file}")
            
            # Автоматический push логов в GitHub после создания summary
            try:
                import subprocess
                log.info("📤 Автоматический push логов в GitHub...")
                
                # Добавляем только папку logs/summaries
                subprocess.run(["git", "add", "logs/summaries/"], check=False, capture_output=True)
                
                # Проверяем, есть ли изменения для коммита
                result = subprocess.run(["git", "status", "--porcelain", "logs/summaries/"], 
                                      capture_output=True, text=True, check=False)
                
                if result.stdout.strip():
                    # Есть изменения - делаем коммит и push
                    subprocess.run(["git", "commit", "-m", f"Add iteration summary: {timestamp}"], 
                                 check=False, capture_output=True)
                    subprocess.run(["git", "push", "origin", "testing-logs"], 
                                 check=False, capture_output=True)
                    log.info("✅ Логи успешно запушены в GitHub")
                else:
                    log.info("ℹ️  Нет новых изменений в логах для push")
                    
            except Exception as e:
                log.warning(f"⚠️  Не удалось запушить логи в GitHub: {e}")
                # Не критично, продолжаем работу
                
        except Exception as e:
            log.error(f"❌ Ошибка при создании summary: {e}")
            import traceback
            log.error(traceback.format_exc())
        
        log.info("\n" + "=" * 60)
        log.info("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")
        log.info("=" * 60)
        
        # Удаление неполных строк из Google Sheets
        if sheets_writer and sheets_writer.worksheet:
            log.info("\n🧹 Удаление неполных строк из Google Sheets...")
            deleted_count = sheets_writer.delete_incomplete_rows()
            if deleted_count > 0:
                log.info(f"✅ Удалено {deleted_count} неполных строк")
            else:
                log.info("✅ Неполных строк не найдено")
        
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

