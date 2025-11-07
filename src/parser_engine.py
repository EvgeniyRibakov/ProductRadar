"""
Parser Engine - парсинг данных с Pipiads
"""

import asyncio
import re
import time
from typing import List, Dict, Optional, Any
from datetime import datetime

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from . import config
from . import logger
from . import validator

log = logger.get_logger("ParserEngine")


class ProductData:
    """Структура данных товара"""
    def __init__(self):
        self.product_name: str = ""
        self.category: str = ""
        self.pipiads_link: str = ""
        self.videos: List[Dict[str, Any]] = []


class ParserEngine:
    """Парсер данных с Pipiads"""
    
    def __init__(self, page: Page):
        self.page = page
        self.browser_manager = None  # Для доступа к human_delay
    
    def set_browser_manager(self, browser_manager):
        """Установить ссылку на browser_manager для использования human_delay"""
        self.browser_manager = browser_manager
    
    async def human_delay(self, min_seconds: float = 1, max_seconds: float = 3):
        """Имитация человеческой задержки"""
        if self.browser_manager:
            await self.browser_manager.human_delay(min_seconds, max_seconds)
        else:
            delay = asyncio.sleep(1)  # Fallback
            await delay
    
    async def scroll_to_element(self, selector: str, timeout: int = 10000):
        """
        Скроллить до элемента
        
        Args:
            selector: Селектор элемента
            timeout: Таймаут в миллисекундах
        """
        try:
            element = await self.page.wait_for_selector(selector, timeout=timeout, state="visible")
            if element:
                await element.scroll_into_view_if_needed()
                await self.human_delay(0.5, 1)
                return True
        except:
            pass
        return False
    
    async def get_products_from_search_page(self, count: int = 3) -> List[Dict[str, str]]:
        """
        Получить список товаров со страницы поиска
        
        Args:
            count: Количество товаров (для MVP-0: 1, потом расширим до 3)
        
        Returns:
            Список словарей с данными товаров: [{"name": "...", "category": "...", "url": "..."}]
        """
        log.info(f"Получение {count} товаров со страницы поиска...")
        
        try:
            # Ждем загрузки страницы
            await self.page.wait_for_load_state("networkidle")
            await self.human_delay(2, 3)
            
            # Скроллим вниз, чтобы загрузились карточки товаров
            log.info("Скроллим страницу для загрузки карточек товаров...")
            for i in range(3):  # Скроллим несколько раз
                await self.page.evaluate("window.scrollBy(0, 500)")
                await self.human_delay(1, 2)
            
            # Ждем появления карточек товаров
            await self.human_delay(2, 3)
            
            # Ищем карточки товаров - пробуем разные селекторы
            product_selectors = [
                'a[href*="/tiktok-shop-product/"]',
                '[class*="product"]',
                '[class*="card"]',
                'div[class*="item"]',
            ]
            
            products = []
            product_links = set()  # Для избежания дубликатов
            
            for selector in product_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    log.debug(f"Найдено {len(elements)} элементов с селектором {selector}")
                    
                    for element in elements:
                        if len(products) >= count:
                            break
                        
                        try:
                            # Пробуем получить ссылку
                            href = await element.get_attribute("href")
                            if not href:
                                # Если элемент не ссылка, ищем ссылку внутри
                                link_element = await element.query_selector('a[href*="/tiktok-shop-product/"]')
                                if link_element:
                                    href = await link_element.get_attribute("href")
                            
                            if href and "/tiktok-shop-product/" in href:
                                # Формируем полный URL
                                if href.startswith("/"):
                                    url = f"https://www.pipiads.com{href}"
                                elif href.startswith("http"):
                                    url = href
                                else:
                                    url = f"https://www.pipiads.com/{href}"
                                
                                # Проверяем, что это новый товар
                                if url in product_links:
                                    continue
                                product_links.add(url)
                                
                                # Пробуем получить название товара
                                name = ""
                                name_selectors = [
                                    'h1', 'h2', 'h3',
                                    '[class*="title"]',
                                    '[class*="name"]',
                                    'a',
                                ]
                                
                                for name_sel in name_selectors:
                                    try:
                                        name_elem = await element.query_selector(name_sel)
                                        if name_elem:
                                            name = await name_elem.inner_text()
                                            if name and len(name) > 5:  # Минимальная длина названия
                                                break
                                    except:
                                        continue
                                
                                # Пробуем получить категорию
                                category = ""
                                category_selectors = [
                                    '[class*="category"]',
                                    '[class*="tag"]',
                                    'span',
                                ]
                                
                                for cat_sel in category_selectors:
                                    try:
                                        cat_elem = await element.query_selector(cat_sel)
                                        if cat_elem:
                                            text = await cat_elem.inner_text()
                                            if text and len(text) < 50:  # Категория обычно короткая
                                                category = text
                                                break
                                    except:
                                        continue
                                
                                if url:
                                    products.append({
                                        "name": name.strip() if name else "N/A",
                                        "category": category.strip() if category else "N/A",
                                        "url": url
                                    })
                                    log.info(f"Найден товар {len(products)}: {name[:50] if name else 'N/A'}...")
                                
                        except Exception as e:
                            log.debug(f"Ошибка при обработке элемента: {e}")
                            continue
                    
                    if len(products) >= count:
                        break
                        
                except Exception as e:
                    log.debug(f"Ошибка с селектором {selector}: {e}")
                    continue
            
            if len(products) < count:
                log.warning(f"Найдено только {len(products)} товаров из {count} запрошенных")
            
            log.info(f"✅ Получено {len(products)} товаров")
            return products[:count]
            
        except Exception as e:
            log.error(f"Ошибка при получении товаров: {e}")
            import traceback
            log.error(traceback.format_exc())
            return []
    
    async def get_product_details(self, product_url: str) -> ProductData:
        """
        Получить детали товара и видео
        
        Args:
            product_url: URL страницы товара
        
        Returns:
            ProductData с данными товара и видео
        """
        log.info("=" * 80)
        log.info(f"🔄 НАЧАЛО ОБРАБОТКИ ТОВАРА")
        log.info(f"URL: {product_url}")
        log.info("=" * 80)
        
        product_data = ProductData()
        product_data.pipiads_link = product_url
        
        # Проверка наличия page
        if not self.page:
            log.error("❌ ОШИБКА: page не инициализирован!")
            return product_data
        
        try:
            # ШАГ 1: Переход на страницу товара
            log.info("\n📌 ШАГ 1: Переход на страницу товара...")
            try:
                log.info(f"  → Загрузка страницы: {product_url}")
                if not self.page:
                    raise Exception("Page не инициализирован!")
                await self.page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
                log.info("  ✅ Страница загружена")
            except Exception as e:
                log.error(f"  ❌ ОШИБКА при загрузке страницы: {e}")
                log.error(f"  → Тип ошибки: {type(e).__name__}")
                import traceback
                log.error(f"  → Трассировка:\n{traceback.format_exc()}")
                # Пробуем подождать еще немного и проверить состояние
                try:
                    await self.human_delay(2, 3)
                    # Проверяем, что страница все еще доступна
                    if self.page:
                        current_url = self.page.url
                        log.info(f"  → Текущий URL: {current_url}")
                except Exception as e2:
                    log.error(f"  ❌ Критическая ошибка: {e2}")
                    return product_data
            
            try:
                await self.human_delay(0.5, 1)
            except Exception as e:
                log.warning(f"  ⚠️ Ошибка при задержке: {e}")
            
            # ШАГ 1.5: Перевод страницы на английский язык
            log.info("\n📌 ШАГ 1.5: Перевод страницы на английский язык...")
            try:
                current_url = self.page.url
                log.info(f"  → Текущий URL: {current_url}")
                
                # Если URL содержит /ru/, заменяем на /en/
                if "/ru/" in current_url:
                    english_url = current_url.replace("/ru/", "/en/")
                    log.info(f"  → Переход на английскую версию: {english_url}")
                    await self.page.goto(english_url, wait_until="domcontentloaded", timeout=30000)
                    await self.human_delay(1, 2)
                    log.info("  ✅ Страница переведена на английский")
                else:
                    # Пробуем найти переключатель языка
                    log.info("  → Поиск переключателя языка...")
                    lang_selectors = [
                        'a[href*="/en/"]',
                        'button:has-text("English")',
                        '[class*="language"]',
                        '[class*="lang"]',
                        'select[name*="lang"]',
                    ]
                    
                    lang_found = False
                    for selector in lang_selectors:
                        try:
                            lang_element = await self.page.query_selector(selector)
                            if lang_element:
                                is_visible = await lang_element.is_visible()
                                if is_visible:
                                    await lang_element.click()
                                    await self.human_delay(1, 2)
                                    log.info(f"  ✅ Переключатель языка найден и нажат: {selector}")
                                    lang_found = True
                                    break
                        except:
                            continue
                    
                    if not lang_found:
                        log.warning("  ⚠️ Переключатель языка не найден, продолжаем на текущем языке")
            except Exception as e:
                log.warning(f"  ⚠️ Ошибка при переводе страницы: {e}, продолжаем...")
            
            # ШАГ 2: Извлечение Product Name
            log.info("\n📌 ШАГ 2: Извлечение Product Name...")
            try:
                # Скроллим вверх для поиска названия товара
                log.info("  → Скроллим вверх для поиска названия товара...")
                if not self.page:
                    raise Exception("Page не инициализирован!")
                await self.page.evaluate("window.scrollTo(0, 0)")
                await self.human_delay(0.3, 0.5)
            except Exception as e:
                log.error(f"  ❌ Ошибка при скролле: {e}")
                # Продолжаем работу
            
            # Получение названия товара - пробуем больше селекторов
            log.info("  → Поиск названия товара через селекторы...")
            try:
                # Важно: берем первый h1, который не содержит служебной информации
                name_selectors = [
                    'h1:first-of-type',
                    'h1[class*="product"]',
                    'h1[class*="title"]',
                    '[class*="product-title"]:not([class*="stock"]):not([class*="remain"])',
                    '[class*="product-name"]',
                    'h1',
                    'h2:first-of-type',
                    '[data-testid*="title"]',
                    '[data-testid*="name"]',
                ]
                
                for selector in name_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            name = await element.inner_text()
                            if name and len(name) > 3:
                                # Фильтруем служебные тексты
                                name_lower = name.lower()
                                if any(skip in name_lower for skip in ['остаток', 'remain', 'stock', 'месяц', 'month', 'комиссия', 'commission']):
                                    continue
                                product_data.product_name = name.strip()
                                log.info(f"  ✅ Название товара найдено: {product_data.product_name[:50]}...")
                                break
                        if product_data.product_name:
                            break
                    except:
                        continue
                
                # Если не нашли, пробуем получить из URL или мета-тегов
                if not product_data.product_name or product_data.product_name == "":
                    try:
                        # Пробуем получить из title страницы
                        title = await self.page.title()
                        if title and len(title) > 3:
                            product_data.product_name = title.strip()
                            log.info(f"  ✅ Название товара найдено (из title): {product_data.product_name[:50]}...")
                    except Exception as e:
                        log.debug(f"  → Ошибка при получении title: {e}")
            except Exception as e:
                log.error(f"  ❌ Ошибка при извлечении названия товара: {e}")
            
            if not product_data.product_name or product_data.product_name == "":
                log.warning("  ⚠️ Название товара не найдено, будет установлено 'N/A'")
                product_data.product_name = "N/A"
            
            # ШАГ 3: Извлечение Category
            log.info("\n📌 ШАГ 3: Извлечение Category...")
            try:
                log.info("  → Поиск категории товара...")
                category_selectors = [
                    '[class*="category"]',
                    '[class*="tag"]',
                    'span:has-text("Category")',
                ]
                
                for selector in category_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            category = await element.inner_text()
                            if category and len(category) < 100:
                                product_data.category = category.strip()
                                log.info(f"  ✅ Категория найдена: {product_data.category}")
                                break
                    except:
                        continue
                
                if not product_data.category:
                    log.warning("  ⚠️ Категория не найдена, будет установлена 'N/A'")
                    product_data.category = "N/A"
            except Exception as e:
                log.error(f"  ❌ Ошибка при извлечении категории: {e}")
                product_data.category = "N/A"
            
            # ШАГ 4: Поиск блока "TikTok Ads"
            log.info("\n📌 ШАГ 4: Поиск блока 'TikTok Ads'...")
            log.info("  → Сначала прокручиваем страницу вниз для загрузки контента...")
            
            # КРИТИЧНО: Прокручиваем страницу вниз, чтобы загрузить весь контент
            # Блок "TikTok Ads" может быть внизу страницы
            try:
                log.info("  → Прокрутка страницы вниз (постепенно)...")
                # Получаем высоту страницы
                page_height = await self.page.evaluate("document.body.scrollHeight")
                viewport_height = await self.page.evaluate("window.innerHeight")
                log.info(f"  → Высота страницы: {page_height}px, высота viewport: {viewport_height}px")
                
                # Прокручиваем постепенно (как человек)
                scroll_steps = max(3, page_height // viewport_height)
                scroll_step = page_height // scroll_steps
                
                for step in range(scroll_steps):
                    scroll_position = scroll_step * (step + 1)
                    await self.page.evaluate(f"window.scrollTo(0, {scroll_position})")
                    await self.human_delay(0.3, 0.5)
                    log.debug(f"  → Прокрутка: {scroll_position}/{page_height}px")
                
                # Прокручиваем до самого низа
                await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await self.human_delay(1, 2)  # Ждем загрузки контента
                log.info("  ✅ Страница прокручена вниз")
            except Exception as e:
                log.warning(f"  ⚠️ Ошибка при прокрутке: {e}, продолжаем...")
            
            log.info("  → Используем текстовый поиск (как Ctrl+F)...")
            tiktok_ads_found = False
            tiktok_ads_element = None
            
            # Сначала ждем загрузки контента
            await self.human_delay(0.5, 1)
            
            # Варианты текста для поиска (английский и русский)
            tiktok_ads_texts = [
                "TikTok Ads",  # Английский
                "Реклама ТикТок",  # Русский вариант 1
                "Реклама TikTok",  # Русский вариант 2
                "TikTok Реклама",  # Русский вариант 3
            ]
            
            # Пробуем найти блок через локатор с текстом (самый надежный способ)
            log.info("  → Попытка 1: Поиск через Playwright locator...")
            for text_variant in tiktok_ads_texts:
                try:
                    # Ищем элемент, содержащий текст (регистронезависимо)
                    locator = self.page.locator(f'text=/{text_variant}/i').first
                    if await locator.count() > 0:
                        tiktok_ads_element = await locator.element_handle()
                        if tiktok_ads_element:
                            # Скроллим к элементу
                            await tiktok_ads_element.scroll_into_view_if_needed()
                            await self.human_delay(0.3, 0.5)
                            tiktok_ads_found = True
                            log.info(f"  ✅ Блок '{text_variant}' найден через Playwright locator")
                            break
                except Exception as e:
                    log.debug(f"Поиск '{text_variant}' через локатор не удался: {e}")
                    continue
            
            # Если не нашли, пробуем через JavaScript поиск (как Ctrl+F)
            if not tiktok_ads_found:
                log.info("  → Попытка 2: Поиск через JavaScript TreeWalker...")
                for text_variant in tiktok_ads_texts:
                    try:
                        # Используем JavaScript для поиска элемента с текстом
                        # Экранируем специальные символы для regex
                        escaped_text = text_variant.replace("\\", "\\\\").replace("/", "\\/")
                        tiktok_ads_element = await self.page.evaluate_handle(f"""
                            () => {{
                                const walker = document.createTreeWalker(
                                    document.body,
                                    NodeFilter.SHOW_TEXT,
                                    null,
                                    false
                                );
                                
                                let node;
                                while (node = walker.nextNode()) {{
                                    if (node.textContent && /{escaped_text}/i.test(node.textContent)) {{
                                        // Находим родительский элемент
                                        let parent = node.parentElement;
                                        while (parent && parent !== document.body) {{
                                            if (parent.offsetHeight > 0 && parent.offsetWidth > 0) {{
                                                return parent;
                                            }}
                                            parent = parent.parentElement;
                                        }}
                                    }}
                                }}
                                return null;
                            }}
                        """)
                        
                        if tiktok_ads_element and await tiktok_ads_element.as_element():
                            element = await tiktok_ads_element.as_element()
                            await element.scroll_into_view_if_needed()
                            await self.human_delay(0.3, 0.5)
                            tiktok_ads_found = True
                            log.info(f"  ✅ Блок '{text_variant}' найден через JavaScript TreeWalker")
                            break
                    except Exception as e:
                        log.debug(f"JavaScript поиск '{text_variant}' не удался: {e}")
                        continue
            
            # Если все еще не нашли, пробуем через query_selector
            if not tiktok_ads_found:
                log.info("  → Попытка 3: Поиск через query_selector с вариантами текста...")
                try:
                    # Пробуем разные варианты текста (английский и русский)
                    text_variants = []
                    for text in tiktok_ads_texts:
                        text_variants.extend([
                            f'text="{text}"',
                            f'text={text}',
                            f'*:has-text("{text}")',
                        ])
                    
                    for variant in text_variants:
                        try:
                            element = await self.page.query_selector(variant)
                            if element:
                                is_visible = await element.is_visible()
                                if is_visible:
                                    await element.scroll_into_view_if_needed()
                                    await self.human_delay(0.3, 0.5)
                                    tiktok_ads_found = True
                                    tiktok_ads_element = element
                                    log.info(f"  ✅ Блок найден через query_selector: {variant}")
                                    break
                        except:
                            continue
                except Exception as e:
                    log.debug(f"Query selector поиск не удался: {e}")
            
            # Попытка 4: Если все еще не нашли, пробуем прокрутить еще раз и поискать снова
            if not tiktok_ads_found:
                log.info("  → Попытка 4: Повторная прокрутка и поиск...")
                try:
                    # Прокручиваем еще раз медленно
                    await self.page.evaluate("window.scrollTo(0, 0)")  # В начало
                    await self.human_delay(0.5, 1)
                    
                    # Прокручиваем вниз медленно, останавливаясь на каждом шаге
                    page_height = await self.page.evaluate("document.body.scrollHeight")
                    scroll_increment = 300  # Прокручиваем по 300px
                    
                    for scroll_pos in range(0, page_height, scroll_increment):
                        await self.page.evaluate(f"window.scrollTo(0, {scroll_pos})")
                        await self.human_delay(0.2, 0.3)
                        
                        # Пробуем найти на каждой позиции (все варианты текста)
                        for text_variant in tiktok_ads_texts:
                            try:
                                # Заменяем пробелы на \s+ для regex
                                regex_pattern = text_variant.replace(" ", "\\s+")
                                locator = self.page.locator(f'text=/{regex_pattern}/i').first
                                if await locator.count() > 0:
                                    tiktok_ads_element = await locator.element_handle()
                                    if tiktok_ads_element:
                                        await tiktok_ads_element.scroll_into_view_if_needed()
                                        await self.human_delay(0.3, 0.5)
                                        tiktok_ads_found = True
                                        log.info(f"  ✅ Блок '{text_variant}' найден при прокрутке на позиции {scroll_pos}px")
                                        break
                            except:
                                continue
                        
                        if tiktok_ads_found:
                            break
                    
                    if not tiktok_ads_found:
                        # Прокручиваем до самого низа еще раз
                        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await self.human_delay(1, 2)
                        
                        # Последняя попытка поиска (все варианты текста)
                        for text_variant in tiktok_ads_texts:
                            try:
                                # Заменяем пробелы на \s+ для regex
                                regex_pattern = text_variant.replace(" ", "\\s+")
                                locator = self.page.locator(f'text=/{regex_pattern}/i').first
                                if await locator.count() > 0:
                                    tiktok_ads_element = await locator.element_handle()
                                    if tiktok_ads_element:
                                        await tiktok_ads_element.scroll_into_view_if_needed()
                                        await self.human_delay(0.3, 0.5)
                                        tiktok_ads_found = True
                                        log.info(f"  ✅ Блок '{text_variant}' найден в самом низу страницы")
                                        break
                            except:
                                continue
                except Exception as e:
                    log.debug(f"Повторная прокрутка не помогла: {e}")
            
            if not tiktok_ads_found:
                log.error("  ❌ Блок 'TikTok Ads' не найден после всех попыток")
                # Сохраняем скриншот для отладки
                try:
                    screenshot_path = config.SCREENSHOTS_DIR / f"tiktok_ads_not_found_{int(time.time())}.png"
                    await self.page.screenshot(path=str(screenshot_path), full_page=True)
                    log.info(f"  📸 Скриншот сохранен: {screenshot_path}")
                except:
                    pass
                log.error("  ❌ Остановка обработки: блок 'TikTok Ads' не найден")
                return product_data
            
            log.info("  ✅ Блок 'TikTok Ads' успешно найден")
            
            # ШАГ 5: Установка сортировки "First seen"
            log.info("\n📌 ШАГ 5: Установка сортировки 'First seen'...")
            sort_success = await self._set_sort_by_first_seen()
            if not sort_success:
                log.warning("  ⚠️ Не удалось установить сортировку, продолжаем...")
            
            # ШАГ 6: Получение списка видео
            log.info("\n📌 ШАГ 6: Получение списка видео из блока 'TikTok Ads'...")
            videos = await self._get_videos_from_tiktok_ads_block()
            log.info(f"  → Найдено {len(videos)} видео в блоке")
            
            # ШАГ 7: Фильтрация видео
            log.info(f"\n📌 ШАГ 7: Фильтрация видео (impression >= {config.MIN_IMPRESSIONS}, дата <= {config.DAYS_BACK} дней)...")
            filtered_videos = await self._filter_videos(videos)
            log.info(f"  → После фильтрации: {len(filtered_videos)} видео")
            
            # Выбор топ-3 видео (для MVP-0: 1 видео)
            video_count = 1  # Для MVP-0
            selected_videos = filtered_videos[:video_count]
            
            log.info(f"  ✅ Выбрано {len(selected_videos)} видео для обработки")
            
            # ШАГ 8: Получение детальных метрик для каждого видео
            log.info(f"\n📌 ШАГ 8: Получение детальных метрик для {len(selected_videos)} видео...")
            for i, video in enumerate(selected_videos, 1):
                log.info(f"\n  🎬 Обработка видео {i}/{len(selected_videos)}...")
                log.info(f"    → Impression: {video.get('impression', 0)}, First seen: {video.get('first_seen', 'N/A')}")
                video_details = await self._get_video_details(video)
                if video_details:
                    product_data.videos.append(video_details)
                    log.info(f"    ✅ Видео {i} обработано успешно")
                else:
                    log.warning(f"    ⚠️ Не удалось получить детали для видео {i}")
                await self.human_delay(0.5, 1)
            
            # Заполняем N/A для отсутствующих видео (для MVP-0 нужно 1, потом расширим до 3)
            while len(product_data.videos) < video_count:
                product_data.videos.append({
                    "tiktok_link": "N/A",
                    "impression": 0,
                    "script": "N/A",
                    "hook": "N/A",
                    "audience_age": "N/A",
                    "country": "N/A",
                    "first_seen": "N/A",
                })
            
            log.info(f"\n✅ Обработано {len(product_data.videos)} видео для товара")
            log.info("=" * 80)
            log.info("✅ ОБРАБОТКА ТОВАРА ЗАВЕРШЕНА УСПЕШНО")
            log.info("=" * 80)
            return product_data
            
        except Exception as e:
            log.error("\n" + "=" * 80)
            log.error(f"❌ ОШИБКА ПРИ ОБРАБОТКЕ ТОВАРА: {e}")
            log.error("=" * 80)
            import traceback
            log.error(traceback.format_exc())
            return product_data
    
    async def _set_sort_by_first_seen(self) -> bool:
        """
        Установить сортировку "First seen" в dropdown
        
        Returns:
            True если успешно
        """
        log.info("  → Поиск dropdown сортировки...")
        try:
            # Ищем dropdown "Sort by"
            sort_selectors = [
                'select:has-text("Sort by")',
                'select',
                '[class*="sort"]',
                'text="Sort by: First seen"',
                'text="Sort by"',
            ]
            
            dropdown = None
            for selector in sort_selectors:
                try:
                    dropdown = await self.page.query_selector(selector)
                    if dropdown:
                        is_visible = await dropdown.is_visible()
                        if is_visible:
                            log.debug(f"Найден dropdown сортировки: {selector}")
                            break
                        else:
                            dropdown = None
                except:
                    continue
            
            if not dropdown:
                # Пробуем найти по тексту "Sort by: First seen"
                try:
                    sort_text = await self.page.query_selector('text="Sort by: First seen"')
                    if sort_text:
                        # Кликаем на текст, чтобы открыть dropdown
                        await sort_text.click()
                        await self.human_delay(0.5, 1)
                        
                        # Ищем опцию "First seen"
                        first_seen_option = await self.page.query_selector('text="First seen"')
                        if first_seen_option:
                            await first_seen_option.click()
                            await self.human_delay(1, 2)
                            log.info("  ✅ Сортировка 'First seen' установлена (через текст)")
                            return True
                except:
                    pass
                
                log.warning("Dropdown сортировки не найден, пробуем продолжить")
                return False
            
            # Если это select элемент
            tag_name = await dropdown.evaluate("el => el.tagName.toLowerCase()")
            if tag_name == "select":
                # Выбираем опцию через value или текст
                try:
                    log.info("  → Найден select элемент, выбираем опцию 'First seen'...")
                    await dropdown.select_option(label="First seen")
                    await self.human_delay(1, 2)
                    log.info("  ✅ Сортировка 'First seen' установлена (select)")
                    return True
                except:
                    pass
            
            # Если это кастомный dropdown - кликаем и выбираем опцию
            log.info("  → Найден кастомный dropdown, открываем...")
            await dropdown.click()
            await self.human_delay(0.5, 1)
            
            # Ищем опцию "First seen"
            log.info("  → Поиск опции 'First seen'...")
            option_selectors = [
                'text="First seen"',
                'text="Sort by: First seen"',
                '[role="option"]:has-text("First seen")',
            ]
            
            for opt_sel in option_selectors:
                try:
                    option = await self.page.query_selector(opt_sel)
                    if option:
                        await option.click()
                        await self.human_delay(1, 2)
                        log.info("  ✅ Сортировка 'First seen' установлена (кастомный dropdown)")
                        return True
                except:
                    continue
            
            log.warning("  ⚠️ Не удалось установить сортировку 'First seen'")
            return False
            
        except Exception as e:
            log.error(f"  ❌ Ошибка при установке сортировки: {e}")
            return False
    
    async def _get_videos_from_tiktok_ads_block(self) -> List[Dict[str, Any]]:
        """
        Получить список видео из блока TikTok Ads
        
        Returns:
            Список словарей с данными видео
        """
        videos = []
        
        try:
            log.info("  → Ожидание появления карточек видео...")
            # Ждем появления карточек видео
            await self.human_delay(0.5, 1)
            
            # Ищем карточки видео - пробуем разные селекторы
            log.info("  → Поиск карточек видео через селекторы...")
            video_card_selectors = [
                '[class*="video"]',
                '[class*="card"]',
                '[class*="ad"]',
                'div[class*="item"]',
                'a[href*="/ad-search/"]',
            ]
            
            video_elements = []
            for selector in video_card_selectors:
                try:
                    elements = await self.page.query_selector_all(selector)
                    if elements:
                        log.debug(f"Найдено {len(elements)} элементов с селектором {selector}")
                        # Фильтруем только те, что содержат видео (имеют thumbnail или play button)
                        for elem in elements:
                            # Проверяем, что это карточка видео
                            has_play_button = await elem.query_selector('[class*="play"], svg, [class*="thumbnail"]')
                            if has_play_button or '/ad-search/' in str(await elem.get_attribute("href") or ""):
                                video_elements.append(elem)
                        if video_elements:
                            break
                except:
                    continue
            
            log.info(f"  → Найдено {len(video_elements)} карточек видео")
            
            # ОГРАНИЧЕНИЕ: Обрабатываем только первые 50 карточек для скорости
            max_cards = 50
            if len(video_elements) > max_cards:
                log.info(f"  → Ограничение: обрабатываем только первые {max_cards} из {len(video_elements)} карточек")
                video_elements = video_elements[:max_cards]
            
            # Извлекаем данные из каждой карточки
            log.info("  → Извлечение данных из карточек...")
            log.info(f"  → Обработка {len(video_elements)} карточек...")
            
            successful_extractions = 0
            for i, card in enumerate(video_elements, 1):
                try:
                    video_data = await self._extract_video_data_from_card(card, i)
                    if video_data:
                        videos.append(video_data)
                        impression = video_data.get('impression', 0)
                        first_seen = video_data.get('first_seen', 'N/A')
                        if impression > 0 or first_seen != 'N/A':
                            successful_extractions += 1
                            if i <= 5:  # Логируем первые 5 для отладки
                                log.info(f"  ✅ Видео {i}: impression={impression}, first_seen={first_seen}")
                except Exception as e:
                    if i <= 5:  # Логируем ошибки первых 5
                        log.warning(f"  ⚠️ Ошибка при извлечении данных из карточки {i}: {e}")
                    continue
            
            log.info(f"  ✅ Извлечено {len(videos)} видео из блока (успешно распарсено: {successful_extractions})")
            return videos
            
        except Exception as e:
            log.error(f"  ❌ Ошибка при получении видео: {e}")
            return []
    
    async def _extract_video_data_from_card(self, card_element, card_index: int = 0) -> Optional[Dict[str, Any]]:
        """
        Извлечь данные из карточки видео
        
        Args:
            card_element: Элемент карточки видео
            card_index: Индекс карточки (для логирования)
        
        Returns:
            Словарь с данными видео или None
        """
        try:
            video_data = {
                "ad_search_url": None,
                "impression": 0,
                "first_seen": None,
                "card_element": card_element,  # Сохраняем для клика
            }
            
            # Получаем текст карточки
            card_text = await card_element.inner_text()
            if card_index <= 3:  # Логируем первые 3 карточки для отладки
                log.debug(f"  → Карточка {card_index}: текст (первые 300 символов): {card_text[:300]}...")
            
            # Также получаем HTML для более точного поиска
            try:
                card_html = await card_element.inner_html()
            except:
                card_html = ""
            
            # Ищем impression в тексте - пробуем разные форматы
            # В карточке может быть просто число типа "6.5K", "2.1M" без слова "Impression"
            # Также ищем на русском: "Показы"
            impression_patterns = [
                r'Impression[:\s]+([\d.,]+[KM]?)',  # "Impression: 6.5K" (англ.)
                r'([\d.,]+[KM]?)\s*Impression',     # "6.5K Impression" (англ.)
                r'Impression[:\s]+([\d,]+)',        # "Impression: 6500" (англ.)
                r'Показы[:\s]+([\d.,]+[KM]?)',      # "Показы: 6.5K" (рус.)
                r'([\d.,]+[KM]?)\s*Показы',        # "6.5K Показы" (рус.)
                r'Показы[:\s]+([\d,]+)',           # "Показы: 6500" (рус.)
            ]
            
            # Сначала ищем с явным упоминанием "Impression" или "Показы"
            found_impression = False
            for pattern in impression_patterns:
                match = re.search(pattern, card_text, re.IGNORECASE)
                if match:
                    impression_str = match.group(1)
                    impression = validator.parse_impressions(impression_str)
                    if impression and impression >= 1000:  # Минимум 1K
                        video_data["impression"] = impression
                        found_impression = True
                        if card_index <= 3:
                            log.debug(f"  → Карточка {card_index}: найдено impression через паттерн '{pattern}': {impression}")
                        break
            
            # Если не нашли с "Impression"/"Показы", ищем просто большие числа (>= 1K)
            # Но только если они выглядят как impressions (обычно самые большие числа на карточке)
            if not found_impression:
                matches = re.findall(r'\b([\d.,]+[KM])\b', card_text)
                # Сортируем по убыванию значения, берем самое большое
                impressions_found = []
                for match_str in matches:
                    impression = validator.parse_impressions(match_str)
                    if impression and impression >= 1000:  # Минимум 1K
                        impressions_found.append((impression, match_str))
                
                if impressions_found:
                    # Берем самое большое число (скорее всего это impression)
                    impressions_found.sort(reverse=True, key=lambda x: x[0])
                    video_data["impression"] = impressions_found[0][0]
                    if card_index <= 3:
                        log.debug(f"  → Карточка {card_index}: найдено impression как большое число: {impressions_found[0][0]} ({impressions_found[0][1]})")
            
            # Ищем дату first_seen (формат "Nov 02 2025-Nov 05 2025" или "Nov 02 2025")
            # Важно: берем ПЕРВУЮ дату из диапазона
            # Также ищем "First seen" или "Впервые замечено"
            date_patterns = [
                r'First\s+seen[:\s]+([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})',  # "First seen: Nov 02 2025" (англ.)
                r'Впервые\s+замечено[:\s]+([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})',  # "Впервые замечено: Nov 02 2025" (рус.)
                r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})\s*-\s*[A-Z][a-z]{2}\s+\d{1,2}\s+\d{4}',  # "Nov 02 2025 - Nov 05 2025"
                r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})',  # "Nov 02 2025" (любая дата)
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, card_text)
                if match:
                    date_str = match.group(1)
                    # Проверяем, что это валидная дата
                    parsed_date = validator.parse_video_date(date_str)
                    if parsed_date:
                        video_data["first_seen"] = date_str
                        if card_index <= 3:
                            log.debug(f"  → Карточка {card_index}: найдена дата first_seen: {date_str}")
                        break
            
            # Ищем ссылку на ad-search
            try:
                link_element = await card_element.query_selector('a[href*="/ad-search/"]')
                if link_element:
                    href = await link_element.get_attribute("href")
                    if href:
                        if href.startswith("/"):
                            video_data["ad_search_url"] = f"https://www.pipiads.com{href}"
                        elif href.startswith("http"):
                            video_data["ad_search_url"] = href
                        else:
                            video_data["ad_search_url"] = f"https://www.pipiads.com/{href}"
            except:
                pass
            
            # Если не нашли ссылку, но есть карточка - можно будет кликнуть на неё
            if not video_data["ad_search_url"]:
                # Сохраняем элемент для клика
                video_data["card_element"] = card_element
            
            return video_data
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении данных из карточки: {e}")
            return None
    
    async def _filter_videos(self, videos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Фильтрация видео по критериям
        
        Args:
            videos: Список видео для фильтрации
        
        Returns:
            Отфильтрованный список видео
        """
        filtered = []
        
        for video in videos:
            # Проверка impression
            impression = video.get("impression", 0)
            if not validator.validate_impressions(impression, config.MIN_IMPRESSIONS):
                log.debug(f"Видео пропущено: impression {impression} < {config.MIN_IMPRESSIONS}")
                continue
            
            # Проверка даты (если есть)
            first_seen = video.get("first_seen")
            if first_seen and first_seen != "N/A" and first_seen is not None:
                parsed_date = validator.parse_video_date(first_seen)
                if parsed_date:
                    if not validator.is_date_within_days(parsed_date, config.DAYS_BACK):
                        log.debug(f"Видео пропущено: дата {first_seen} старше {config.DAYS_BACK} дней")
                        continue
                else:
                    # Если не удалось распарсить, но есть impression >= 50k, пропускаем проверку даты
                    if impression >= config.MIN_IMPRESSIONS:
                        log.debug(f"Видео принято: не удалось распарсить дату {first_seen}, но impression {impression} >= {config.MIN_IMPRESSIONS}")
                    else:
                        log.debug(f"Видео пропущено: не удалось распарсить дату {first_seen} и impression {impression} < {config.MIN_IMPRESSIONS}")
                        continue
            # Если даты нет, но impression >= 50k, принимаем видео
            elif impression >= config.MIN_IMPRESSIONS:
                log.debug(f"Видео принято: нет даты, но impression {impression} >= {config.MIN_IMPRESSIONS}")
            else:
                log.debug("Видео пропущено: нет даты first_seen и impression < минимума")
                continue
            
            filtered.append(video)
        
        # Сортировка по приоритету: сначала >= 100k, потом >= 50k
        filtered.sort(key=lambda v: (
            0 if v.get("impression", 0) >= config.PRIORITY_IMPRESSIONS else 1,
            -v.get("impression", 0)  # По убыванию impression
        ))
        
        log.info(f"✅ Отфильтровано {len(filtered)} видео из {len(videos)}")
        return filtered
    
    async def _get_video_details(self, video: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Получить детальные метрики видео
        
        Args:
            video: Словарь с базовыми данными видео (из карточки)
        
        Returns:
            Словарь с полными данными видео
        """
        try:
            # Если есть ad_search_url, переходим напрямую
            if video.get("ad_search_url"):
                log.info(f"    → Переход на страницу ad-search: {video['ad_search_url']}")
                await self.page.goto(video["ad_search_url"], wait_until="domcontentloaded", timeout=30000)
                await self.human_delay(0.5, 1)
                log.info("    ✅ Страница ad-search загружена")
            else:
                # Если нет URL, кликаем на карточку
                card_element = video.get("card_element")
                if not card_element:
                    log.error("    ❌ Нет способа перейти к видео (нет URL и элемента)")
                    return None
                
                log.info("    → Клик на карточку видео...")
                await card_element.click()
                await self.human_delay(0.5, 1)
                log.info("    ✅ Карточка видео открыта")
                
                # Ждем открытия окна/модального окна
                # Ищем кнопку "More detail"
                log.info("    → Поиск кнопки 'More detail'...")
                more_detail_selectors = [
                    'text="More detail"',
                    'text="More Detail"',
                    'button:has-text("More detail")',
                    'a:has-text("More detail")',
                ]
                
                more_detail_button = None
                for selector in more_detail_selectors:
                    try:
                        more_detail_button = await self.page.wait_for_selector(selector, timeout=5000, state="visible")
                        if more_detail_button:
                            log.info(f"    ✅ Найдена кнопка 'More detail' (селектор: {selector})")
                            break
                    except:
                        continue
                
                if not more_detail_button:
                    log.error("    ❌ Кнопка 'More detail' не найдена")
                    return None
                
                # Кликаем на "More detail"
                log.info("    → Клик на кнопку 'More detail'...")
                await more_detail_button.click()
                await self.human_delay(0.5, 1)
                
                # Ждем загрузки страницы ad-search
                log.info("    → Ожидание загрузки страницы ad-search...")
                await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                await self.human_delay(0.3, 0.5)
                log.info("    ✅ Страница ad-search загружена")
            
            # Извлекаем данные со страницы ad-search
            log.info("    → Извлечение данных со страницы ad-search...")
            return await self._extract_ad_search_data()
            
        except Exception as e:
            log.error(f"    ❌ Ошибка при получении деталей видео: {e}")
            import traceback
            log.error(traceback.format_exc())
            return None
    
    async def _extract_ad_search_data(self) -> Dict[str, Any]:
        """
        Извлечь все данные со страницы ad-search
        
        Returns:
            Словарь с данными видео
        """
        video_data = {
            "tiktok_link": "N/A",
            "impression": 0,
            "script": "N/A",
            "hook": "N/A",
            "audience_age": "N/A",
            "country": "N/A",
            "first_seen": "N/A",
        }
        
        try:
            # Ждем загрузки страницы
            await self.page.wait_for_load_state("domcontentloaded")
            await self.human_delay(0.3, 0.5)
            
            # Получаем весь текст страницы для поиска
            page_text = await self.page.content()
            
            # 1. TikTok ссылка (из поля "TikTok Post" или "Пост TikTok")
            tiktok_link_selectors = [
                'a[href*="tiktok.com"]',
                'a[href*="m.tiktok.com"]',
                'text="TikTok Post"',  # Английский приоритет
                'text="Пост TikTok"',  # Русский fallback
            ]
            
            for selector in tiktok_link_selectors:
                try:
                    if 'text=' in selector:
                        # Ищем по тексту и берем ссылку рядом
                        element = await self.page.query_selector(selector)
                        if element:
                            # Ищем ссылку в родительском элементе или рядом
                            try:
                                # Используем locator для поиска родительского элемента
                                locator = self.page.locator(selector).first
                                parent_locator = locator.locator("..")
                                link = await parent_locator.locator('a[href*="tiktok.com"]').first.element_handle()
                                if link:
                                    href = await link.get_attribute("href")
                                    if href:
                                        video_data["tiktok_link"] = href
                                        break
                            except:
                                # Fallback: ищем ссылку на странице
                                link = await self.page.query_selector('a[href*="tiktok.com"]')
                                if link:
                                    href = await link.get_attribute("href")
                                    if href:
                                        video_data["tiktok_link"] = href
                                        break
                    else:
                        link = await self.page.query_selector(selector)
                        if link:
                            href = await link.get_attribute("href")
                            if href and "tiktok.com" in href:
                                video_data["tiktok_link"] = href
                                break
                except:
                    continue
            
            # 2. Impressions - КРИТИЧНО: "Impressions" (англ.) или "Показы" (рус.), не "Likes" или "Нравится"!
            log.info("      → Извлечение impressions...")
            impression_text = await self._extract_impressions()
            if impression_text:
                video_data["impression"] = validator.parse_impressions(impression_text) or 0
                log.info(f"      ✅ Impressions: {video_data['impression']}")
            else:
                log.warning("      ⚠️ Impressions не найдены")
            
            # 3. Script (из "Transcript" или "Анализ транскрипта")
            log.info("      → Извлечение сценария (script)...")
            script = await self._extract_script()
            if script:
                video_data["script"] = script
                log.info(f"      ✅ Script найден ({len(script)} символов)")
            else:
                video_data["script"] = "N/A"
                log.info("      ⚠️ Script не найден, установлено 'N/A'")
            
            # 4. Hook (из секции Hook)
            log.info("      → Извлечение hook...")
            hook = await self._extract_hook()
            if hook:
                video_data["hook"] = hook
                log.info(f"      ✅ Hook найден: {hook[:50]}...")
            else:
                video_data["hook"] = "N/A"
                log.info("      ⚠️ Hook не найден, установлено 'N/A'")
            
            # 5. Audience Age и Country (из Target Audience или Целевая аудитория)
            log.info("      → Извлечение данных аудитории...")
            audience_data = await self._extract_audience()
            if audience_data:
                age = audience_data.get("age", "N/A")
                platform = audience_data.get("platform", "N/A")
                # Форматируем в формате "35-45 Android"
                video_data["audience_age"] = validator.format_audience(age, platform)
                video_data["country"] = audience_data.get("country", "N/A")
                log.info(f"      ✅ Audience: {video_data['audience_age']}, Country: {video_data['country']}")
            else:
                log.info("      ⚠️ Данные аудитории не найдены, установлено 'N/A'")
            
            # 6. First seen (формат "Oct 27 2025")
            log.info("      → Извлечение даты First seen...")
            first_seen = await self._extract_first_seen()
            if first_seen:
                video_data["first_seen"] = first_seen
                log.info(f"      ✅ First seen: {first_seen}")
            else:
                video_data["first_seen"] = "N/A"
                log.info("      ⚠️ First seen не найден, установлено 'N/A'")
            
            log.info(f"    ✅ Все данные извлечены: impression={video_data['impression']}, first_seen={video_data['first_seen']}")
            return video_data
            
        except Exception as e:
            log.error(f"Ошибка при извлечении данных ad-search: {e}")
            return video_data
    
    async def _extract_impressions(self) -> Optional[str]:
        """
        Извлечь impressions - КРИТИЧНО: "Impressions" (англ.) или "Показы" (рус.), не "Likes" или "Нравится"!
        
        Returns:
            Строка с impressions или None
        """
        try:
            # Ищем по тексту "Impressions" или "Показы" - это ключевое слово
            page_text = await self.page.content()
            
            # Паттерн для поиска "Impressions" или "Показы" с числом рядом (приоритет английскому)
            patterns = [
                r'Impression[:\s]+([\d.,]+[KM]?)',  # Английский приоритет
                r'Impression[:\s]+([\d\s]+[KM]?)',
                r'([\d.,]+[KM]?)\s*Impression',
                r'Показы[:\s]*([\d.,]+[KM]?)',  # Русский fallback
                r'Показы[:\s]*([\d\s]+[KM]?)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    impression_str = match.group(1)
                    log.debug(f"Найдено impressions: {impression_str}")
                    return impression_str
            
            # Если не нашли по паттерну, ищем элемент с текстом "Impressions" или "Показы"
            try:
                # Сначала английский
                impression_locator = self.page.locator('text="Impressions"').first
                if await impression_locator.count() == 0:
                    # Fallback на русский
                    impression_locator = self.page.locator('text="Показы"').first
                
                if await impression_locator.count() > 0:
                    # Ищем число рядом с этим элементом - используем locator для родителя
                    parent_text = await impression_locator.locator("..").inner_text()
                    match = re.search(r'([\d.,]+[KM]?)', parent_text)
                    if match:
                        return match.group(1)
            except:
                pass
            
            log.warning("Не удалось найти 'Impressions' или 'Показы'")
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении impressions: {e}")
            return None
    
    async def _extract_script(self) -> Optional[str]:
        """Извлечь сценарий из секции 'Transcript' или 'Анализ транскрипта'"""
        try:
            # Ищем секцию "Transcript" (англ.) или "Анализ транскрипта" (рус.) - приоритет английскому
            transcript_selectors = [
                'text="Transcript"',  # Английский приоритет
                'text="Анализ транскрипта"',  # Русский fallback
                '[class*="transcript"]',
            ]
            
            for selector in transcript_selectors:
                try:
                    locator = self.page.locator(selector).first
                    if await locator.count() > 0:
                        # Ищем текст сценария рядом - используем locator для родителя
                        parent_text = await locator.locator("..").inner_text()
                        # Извлекаем текст после "Transcript" (англ.) или "Анализ транскрипта" (рус.)
                        parts = parent_text.split("Transcript")
                        if len(parts) > 1:
                            script = parts[1].strip()
                            if script and len(script) > 10:
                                return script
                        
                        parts = parent_text.split("Анализ транскрипта")
                        if len(parts) > 1:
                            script = parts[1].strip()
                            if script and len(script) > 10:
                                return script
                except:
                    continue
            
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении сценария: {e}")
            return None
    
    async def _extract_hook(self) -> Optional[str]:
        """Извлечь hook из секции Hook"""
        try:
            hook_selectors = [
                'text="Hook"',
                '[class*="hook"]',
            ]
            
            for selector in hook_selectors:
                try:
                    locator = self.page.locator(selector).first
                    if await locator.count() > 0:
                        # Ищем текст hook рядом - используем locator для родителя
                        parent_text = await locator.locator("..").inner_text()
                        parts = parent_text.split("Hook")
                        if len(parts) > 1:
                            hook = parts[1].strip()
                            if hook and len(hook) > 5:
                                return hook
                except:
                    continue
            
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении hook: {e}")
            return None
    
    async def _extract_audience(self) -> Optional[Dict[str, str]]:
        """Извлечь возраст, платформу и страну из Target Audience"""
        try:
            audience_data = {"age": "N/A", "platform": "N/A", "country": "N/A"}
            
            # Ищем секцию "Target Audience" (англ.) или "Целевая аудитория" (рус.) - приоритет английскому
            audience_selectors = [
                'text="Target Audience"',  # Английский приоритет
                'text="Целевая аудитория"',  # Русский fallback
                '[class*="audience"]',
            ]
            
            for selector in audience_selectors:
                try:
                    locator = self.page.locator(selector).first
                    if await locator.count() > 0:
                        # Ищем текст аудитории рядом - используем locator для родителя
                        text = await locator.locator("..").inner_text()
                        
                        # Ищем возраст (формат "35-45", "18-24" и т.д.)
                        age_match = re.search(r'(\d{1,2}-\d{1,2})', text)
                        if age_match:
                            audience_data["age"] = age_match.group(1)
                        
                        # Ищем платформу (Android, iOS, iPhone, etc.)
                        platform_keywords = ["Android", "iOS", "iPhone", "iPad"]
                        for keyword in platform_keywords:
                            if keyword in text:
                                # Нормализуем: iOS/iPhone/iPad -> iOS, остальное -> Android
                                if keyword in ["iOS", "iPhone", "iPad"]:
                                    audience_data["platform"] = "iOS"
                                else:
                                    audience_data["platform"] = "Android"
                                break
                        
                        # Ищем страну (обычно название страны)
                        country_keywords = ["USA", "US", "United States", "Россия", "Russia", "Philippines", "Филиппины"]
                        for keyword in country_keywords:
                            if keyword in text:
                                audience_data["country"] = keyword
                                break
                        
                        if audience_data["age"] != "N/A" or audience_data["platform"] != "N/A" or audience_data["country"] != "N/A":
                            return audience_data
                except:
                    continue
            
            return audience_data
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении аудитории: {e}")
            return None
    
    async def _extract_first_seen(self) -> Optional[str]:
        """Извлечь First seen в формате 'Oct 27 2025'"""
        try:
            # Ищем "First seen" на странице
            first_seen_selectors = [
                'text="First seen"',
                '[class*="first-seen"]',
            ]
            
            for selector in first_seen_selectors:
                try:
                    locator = self.page.locator(selector).first
                    if await locator.count() > 0:
                        # Ищем текст даты рядом - используем locator для родителя
                        text = await locator.locator("..").inner_text()
                        
                        # Ищем дату в формате "Oct 27 2025"
                        date_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})', text)
                        if date_match:
                            return date_match.group(1)
                except:
                    continue
            
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении first_seen: {e}")
            return None

