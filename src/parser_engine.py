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
            # Ждем загрузки страницы (domcontentloaded быстрее, чем networkidle)
            await self.page.wait_for_load_state("domcontentloaded")
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
    
    async def get_product_details(self, product_url: str, sheets_writer=None) -> ProductData:
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
            
            # Получение названия товара - пробуем больше селекторов и методов
            log.info("  → Поиск названия товара через селекторы...")
            try:
                # Метод 1: Поиск через селекторы (приоритет)
                name_selectors = [
                    'h1:first-of-type',
                    'h1[class*="product"]',
                    'h1[class*="title"]',
                    '[class*="product-title"]',
                    '[class*="product-name"]',
                    '[class*="product_title"]',
                    '[class*="product_name"]',
                    'h1',
                    'h2:first-of-type',
                    '[data-testid*="title"]',
                    '[data-testid*="name"]',
                    '[data-testid*="product-title"]',
                ]
                
                for selector in name_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            name = await element.inner_text()
                            if name and len(name) > 3:
                                # Фильтруем служебные тексты
                                name_lower = name.lower()
                                skip_words = ['остаток', 'remain', 'stock', 'месяц', 'month', 'комиссия', 'commission', 
                                            'tiktok shop product detail', 'category', 'категория']
                                if any(skip in name_lower for skip in skip_words):
                                    continue
                                # Убираем префикс "TikTok Shop Product Detail:" если есть
                                if "TikTok Shop Product Detail:" in name:
                                    name = name.split("TikTok Shop Product Detail:")[-1].strip()
                                # Убираем "TikTok Shop Product" из начала и конца
                                if name.lower().startswith('tiktok shop product'):
                                    name = re.sub(r'^tiktok shop product\s*:?\s*', '', name, flags=re.IGNORECASE).strip()
                                if name.lower().endswith('tiktok shop product'):
                                    name = re.sub(r'\s*tiktok shop product\s*$', '', name, flags=re.IGNORECASE).strip()
                                # Убираем, если это просто "TikTok Shop Product"
                                if name.lower() == 'tiktok shop product' or name.lower() == 'tiktok shop product detail':
                                    continue
                                if ":" in name and len(name.split(":")[0]) < 20:
                                    name = name.split(":", 1)[-1].strip()
                                product_data.product_name = name.strip()
                                if len(product_data.product_name) > 5:
                                    log.info(f"  ✅ Название товара найдено: {product_data.product_name[:50]}...")
                                    break
                        if product_data.product_name and len(product_data.product_name) > 5:
                            break
                    except:
                        continue
                
                # Метод 2: Поиск через JavaScript (более агрессивный - по структуре DOM)
                if not product_data.product_name or len(product_data.product_name) <= 5:
                    try:
                        product_name = await self.page.evaluate("""
                            () => {
                                // Ищем h1
                                const h1 = document.querySelector('h1');
                                if (h1) {
                                    const text = h1.innerText.trim();
                                    if (text && text.length > 5 && !text.toLowerCase().includes('tiktok shop product detail')) {
                                        return text;
                                    }
                                }
                                
                                // Ищем в элементах с классом product
                                const productElements = document.querySelectorAll('[class*="product"][class*="title"], [class*="product"][class*="name"]');
                                for (const el of productElements) {
                                    const text = el.innerText.trim();
                                    if (text && text.length > 5) {
                                        return text;
                                    }
                                }
                                
                                // Ищем самый большой заголовок на странице (обычно это название товара)
                                // НО пропускаем короткие тексты типа "Ad Analysis"
                                const headings = document.querySelectorAll('h1, h2, h3');
                                let maxLength = 0;
                                let bestHeading = null;
                                for (const h of headings) {
                                    const text = h.innerText.trim();
                                    const skipWords = ['tiktok', 'shop', 'product', 'detail', 'category', 'commission', 
                                                      'остаток', 'remain', 'stock', 'ad analysis', 'analysis', 
                                                      'limited time', 'promotion', 'annual plan', 'tiktok shop product'];
                                    const textLower = text.toLowerCase();
                                    // Пропускаем короткие тексты (меньше 20 символов) - это обычно не название товара
                                    // Пропускаем "TikTok Shop Product" и похожие тексты
                                    if (!skipWords.some(word => textLower.includes(word)) && 
                                        text.length > maxLength && text.length > 20 &&
                                        !textLower.includes('tiktok shop product')) {
                                        maxLength = text.length;
                                        bestHeading = text;
                                    }
                                }
                                if (bestHeading) {
                                    return bestHeading;
                                }
                                
                                // Ищем в текстовых блоках - название товара обычно длинное
                                // Например: "[BUY 1 TAKE 11] SHEEureka Scrub Facial Cleanser..."
                                // НО исключаем футер/меню
                                const footerMenuKeywords = ['Privacy', 'Terms', 'Copyright', 'PIPIADS', 'All Rights Reserved',
                                                           'AI-agent', 'cosmobeauty', 'credits', 'subscription', 'invoice',
                                                           'Monthly Credits', 'Extra Credits', 'data cost', 'detail costs',
                                                           'Team Setting', 'Affiliate Dashboard', 'Logout', '@gmail.com',
                                                           'English', 'Français', 'Deutsch', 'Español', 'Português'];
                                const textBlocks = document.querySelectorAll('p, div, span');
                                for (const block of textBlocks) {
                                    const text = block.innerText.trim();
                                    // Проверяем, что это не футер/меню
                                    const isFooterMenu = footerMenuKeywords.some(keyword => text.includes(keyword));
                                    if (isFooterMenu) continue;
                                    
                                    // Название товара обычно длинное (больше 30 символов) и содержит слова типа "Set", "Kit", "Mask" и т.д.
                                    // Или начинается с "[" (например "[BUY 1 TAKE 11]")
                                    if (text.length > 30 && text.length < 500 && 
                                        !text.toLowerCase().includes('ad analysis') &&
                                        !text.toLowerCase().includes('limited time') &&
                                        !text.toLowerCase().includes('promotion') &&
                                        !text.toLowerCase().includes('annual plan') &&
                                        (text.startsWith('[') || text.includes('Set') || text.includes('Kit') || 
                                         text.includes('Mask') || text.includes('Cleanser') || text.includes('Gift') ||
                                         text.includes('Scrub') || text.includes('Facial') || text.includes('Repairing'))) {
                                        return text;
                                    }
                                }
                                
                                // Ищем в мета-тегах
                                const ogTitle = document.querySelector('meta[property="og:title"]');
                                if (ogTitle && ogTitle.content) {
                                    let title = ogTitle.content;
                                    if (title.includes('TikTok Shop Product Detail:')) {
                                        title = title.split('TikTok Shop Product Detail:')[1].trim();
                                    }
                                    // Убираем "TikTok Shop Product" из начала
                                    if (title.toLowerCase().startsWith('tiktok shop product')) {
                                        title = title.replace(/^tiktok shop product\s*:?\s*/i, '').trim();
                                    }
                                    if (title && title.length > 5 && !title.toLowerCase().includes('tiktok shop product')) {
                                        return title;
                                    }
                                }
                                
                                return null;
                            }
                        """)
                        if product_name and len(product_name) > 5:
                            product_name = product_name.strip()
                            # Убираем "TikTok Shop Product" из начала и конца
                            if product_name.lower().startswith('tiktok shop product'):
                                product_name = re.sub(r'^tiktok shop product\s*:?\s*', '', product_name, flags=re.IGNORECASE).strip()
                            if product_name.lower().endswith('tiktok shop product'):
                                product_name = re.sub(r'\s*tiktok shop product\s*$', '', product_name, flags=re.IGNORECASE).strip()
                            # Убираем, если это просто "TikTok Shop Product"
                            if product_name.lower() == 'tiktok shop product' or product_name.lower() == 'tiktok shop product detail':
                                product_name = None
                            if product_name and len(product_name) > 5:
                                product_data.product_name = product_name
                                log.info(f"  ✅ Название товара найдено (через JS): {product_data.product_name[:50]}...")
                    except Exception as e:
                        log.debug(f"  → Ошибка при поиске через JS: {e}")
            except Exception as e:
                log.error(f"  ❌ Ошибка при извлечении названия товара: {e}")
            
            if not product_data.product_name or len(product_data.product_name) <= 5:
                log.warning("  ⚠️ Название товара не найдено, будет установлено 'N/A'")
                product_data.product_name = "N/A"
            
            # ШАГ 3: Извлечение Category
            log.info("\n📌 ШАГ 3: Извлечение Category...")
            try:
                log.info("  → Поиск категории товара...")
                
                # Метод 1: Поиск через селекторы
                category_selectors = [
                    '[class*="category"]',
                    '[class*="tag"]',
                    'span:has-text("Category")',
                    'span:has-text("Категория")',
                    'text=/Category/i',
                    'text=/Категория/i',
                    'div:has-text("Category")',
                    'div:has-text("Категория")',
                ]
                
                for selector in category_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            category = await element.inner_text()
                            if category:
                                # Очищаем от лишнего текста
                                category = re.sub(r'Category\s*:', '', category, flags=re.IGNORECASE)
                                category = re.sub(r'Категория\s*:', '', category, flags=re.IGNORECASE)
                                category = re.sub(r'Commission\s*Rate\s*:.*', '', category, flags=re.IGNORECASE)
                                category = re.sub(r'Комиссия\s*:.*', '', category, flags=re.IGNORECASE)
                                # Убираем проценты (например "15.00%")
                                category = re.sub(r'\s*\d+\.?\d*\s*%', '', category)
                                # Убираем лишние символы > и пробелы
                                category = re.sub(r'\s*>\s*', ' > ', category)
                                category = category.strip()
                                # Берем только первую часть до "Commission" или ограничиваем длину
                                if "Commission" in category or "Комиссия" in category:
                                    category = category.split("Commission")[0].split("Комиссия")[0].strip()
                                if len(category) > 100:
                                    category = category[:100]
                                if category and len(category) > 3:
                                    product_data.category = category
                                    log.info(f"  ✅ Категория найдена: {product_data.category}")
                                    break
                        if product_data.category:
                            break
                    except:
                        continue
                
                # Метод 2: Поиск через JavaScript (более агрессивный)
                if not product_data.category:
                    try:
                        category = await self.page.evaluate("""
                            () => {
                                // Ищем элементы с текстом "Category" или "Категория"
                                const allElements = document.querySelectorAll('*');
                                for (const el of allElements) {
                                    const text = el.innerText || '';
                                    if (text.includes('Category') || text.includes('Категория')) {
                                        // Извлекаем категорию после "Category:" или "Категория:"
                                        let categoryText = text;
                                        if (categoryText.includes('Category:')) {
                                            categoryText = categoryText.split('Category:')[1];
                                        } else if (categoryText.includes('Категория:')) {
                                            categoryText = categoryText.split('Категория:')[1];
                                        }
                                        
                                        // Убираем "Commission Rate" и все после
                                        if (categoryText.includes('Commission Rate') || categoryText.includes('Комиссия')) {
                                            categoryText = categoryText.split('Commission Rate')[0].split('Комиссия')[0];
                                        }
                                        
                                        // Убираем проценты (например "15.00%")
                                        categoryText = categoryText.replace(/\s*\d+\.?\d*\s*%/g, '');
                                        
                                        categoryText = categoryText.trim();
                                        
                                        // Проверяем, что это похоже на категорию (содержит ">" или несколько слов)
                                        if (categoryText && categoryText.length > 3 && 
                                            (categoryText.includes('>') || categoryText.split(' ').length >= 2)) {
                                            return categoryText.substring(0, 100);
                                        }
                                    }
                                }
                                return null;
                            }
                        """)
                        if category and len(category) > 3:
                            product_data.category = category.strip()
                            log.info(f"  ✅ Категория найдена (через JS): {product_data.category}")
                    except Exception as e:
                        log.debug(f"  → Ошибка при поиске категории через JS: {e}")
                
                if not product_data.category:
                    log.warning("  ⚠️ Категория не найдена, будет установлена 'N/A'")
                    product_data.category = "N/A"
            except Exception as e:
                log.error(f"  ❌ Ошибка при извлечении категории: {e}")
                product_data.category = "N/A"
            
            # ШАГ 3.5: Запись базовых данных в Google Sheets (если sheets_writer передан)
            # ВАЖНО: Если ячейки защищены, пропускаем запись базовых данных и записываем только видео
            if sheets_writer:
                log.info("\n📌 ШАГ 3.5: Запись базовых данных в Google Sheets...")
                try:
                    row_number = sheets_writer.write_basic_product_data(
                        product_data.product_name,
                        product_data.category,
                        product_data.pipiads_link
                    )
                    if row_number > 0:
                        # Сохраняем номер строки для последующей записи видео
                        product_data._sheets_row = row_number
                        log.info(f"  ✅ Базовые данные записаны в Google Sheets (строка {row_number})")
                    else:
                        # Если не удалось записать базовые данные (возможно, ячейки защищены),
                        # находим пустую строку для записи только видео данных
                        log.warning("  ⚠️ Ошибка при записи базовых данных (возможно, ячейки защищены)")
                        log.info("  → Находим пустую строку для записи видео данных...")
                        row_number = sheets_writer.find_next_empty_row()
                        product_data._sheets_row = row_number
                        log.info(f"  ✅ Будем записывать видео данные в строку {row_number}")
                except Exception as e:
                    log.warning(f"  ⚠️ Ошибка при записи базовых данных: {e}")
                    # Находим пустую строку для записи только видео
                    try:
                        row_number = sheets_writer.find_next_empty_row()
                        product_data._sheets_row = row_number
                        log.info(f"  → Будем записывать видео данные в строку {row_number}")
                    except:
                        pass
            
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
            
            # Выбор топ-3 видео
            video_count = 3
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
            
            # Заполняем N/A для отсутствующих видео (нужно 3 видео)
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
            # Проверка impression (может быть строкой "170.6K" или числом)
            impression = video.get("impression", 0)
            impression_num = 0
            if isinstance(impression, str):
                # Парсим строку в число для сравнения
                impression_num = validator.parse_impressions(impression) or 0
            elif isinstance(impression, (int, float)):
                impression_num = int(impression)
            
            if not validator.validate_impressions(impression_num, config.MIN_IMPRESSIONS):
                log.debug(f"Видео пропущено: impression {impression} ({impression_num}) < {config.MIN_IMPRESSIONS}")
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
            
            # Сохраняем числовое значение для сортировки
            video["_impression_num"] = impression_num
            filtered.append(video)
        
        # Сортировка: сначала по дате (самые недавние), потом по impressions (самые большие)
        # Убираем дубликаты по tiktok_link или ad_search_url
        seen_videos = set()
        unique_videos = []
        for video in filtered:
            # Используем tiktok_link или ad_search_url для определения уникальности
            video_id = video.get("tiktok_link") or video.get("ad_search_url") or str(video.get("impression", ""))
            if video_id not in seen_videos:
                seen_videos.add(video_id)
                unique_videos.append(video)
        
        # Сортируем: сначала по дате (самые недавние), потом по impressions (самые большие)
        def sort_key(v):
            parsed_date = validator.parse_video_date(v.get("first_seen", ""))
            if parsed_date:
                date_timestamp = -parsed_date.timestamp()  # Отрицательное для сортировки по убыванию (самые недавние)
            else:
                date_timestamp = 0  # Видео без даты в конец
            return (date_timestamp, -v.get("_impression_num", 0))
        
        unique_videos.sort(key=sort_key)
        
        # Берем топ-3
        top_videos = unique_videos[:3]
        
        log.info(f"✅ Отфильтровано {len(filtered)} видео из {len(videos)}, уникальных: {len(unique_videos)}, топ-3: {len(top_videos)}")
        return top_videos
    
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
                # ВАЖНО: Элемент может исчезнуть из DOM, поэтому ищем его заново
                card_element = video.get("card_element")
                if not card_element:
                    log.error("    ❌ Нет способа перейти к видео (нет URL и элемента)")
                    return None
                
                log.info("    → Клик на карточку видео...")
                try:
                    # Проверяем, что элемент еще в DOM
                    is_attached = await card_element.evaluate("el => el.isConnected")
                    if not is_attached:
                        log.warning("    ⚠️ Элемент исчез из DOM, пытаемся найти заново...")
                        # Пытаемся найти элемент заново по ad_search_url или другим признакам
                        # Если не получается, возвращаем None
                        log.error("    ❌ Не удалось найти элемент заново")
                        return None
                    
                    await card_element.click()
                    await self.human_delay(0.5, 1)
                    log.info("    ✅ Карточка видео открыта")
                except Exception as e:
                    log.error(f"    ❌ Ошибка при клике на карточку: {e}")
                    log.warning("    ⚠️ Пытаемся найти элемент заново...")
                    # Если элемент исчез, возвращаем None
                    return None
                
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
            # Передаем исходные данные видео (impressions из карточки) для fallback
            log.info("    → Извлечение данных со страницы ad-search...")
            return await self._extract_ad_search_data(video)
            
        except Exception as e:
            log.error(f"    ❌ Ошибка при получении деталей видео: {e}")
            import traceback
            log.error(traceback.format_exc())
            return None
    
    async def _extract_ad_search_data(self, original_video: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Извлечь все данные со страницы ad-search
        
        Args:
            original_video: Исходные данные видео из карточки (для fallback impressions)
        
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
        
        # Сохраняем impressions из карточки для fallback
        if original_video:
            original_impression = original_video.get("impression")
            if original_impression:
                video_data["_original_impression"] = original_impression
        
        try:
            # Ждем загрузки страницы
            await self.page.wait_for_load_state("domcontentloaded")
            await self.human_delay(0.3, 0.5)
            
            # Получаем весь текст страницы для поиска
            page_text = await self.page.content()
            
            # 1. TikTok ссылка (из поля "TikTok Post" (англ.) или "Пост TikTok" (рус.))
            log.info("      → Извлечение TikTok ссылки...")
            
            # Сначала ищем по тексту "TikTok Post" или "Пост TikTok"
            tiktok_post_selectors = [
                'text=/TikTok Post/i',  # Английский приоритет
                'text=/Пост TikTok/i',  # Русский fallback
            ]
            
            for selector in tiktok_post_selectors:
                try:
                    locator = self.page.locator(selector).first
                    if await locator.count() > 0:
                        # Ищем ссылку рядом
                        try:
                            parent_locator = locator.locator("..")
                            # Ищем ссылку на видео (приоритет ссылкам с /v/)
                            link = await parent_locator.locator('a[href*="m.tiktok.com/v/"]').first.element_handle()
                            if not link:
                                link = await parent_locator.locator('a[href*="tiktok.com/v/"]').first.element_handle()
                            if not link:
                                link = await parent_locator.locator('a[href*="tiktok.com"]').first.element_handle()
                            if link:
                                href = await link.get_attribute("href")
                                if href:
                                    # КРИТИЧНО: Пропускаем ссылки на товары в TikTok Shop
                                    if "shop.tiktok.com/view/product" in href or "/view/product" in href:
                                        log.debug(f"      → Пропущена ссылка на товар: {href[:50]}...")
                                        continue
                                    # Берем только ссылки на видео
                                    if "/v/" in href or "m.tiktok.com" in href:
                                        video_data["tiktok_link"] = href
                                        log.info(f"      ✅ TikTok ссылка найдена: {href[:50]}...")
                                        break
                        except:
                            pass
                except:
                    continue
            
            # Если не нашли через текст, ищем все ссылки на TikTok
            # ВАЖНО: Берем только ссылки на видео (m.tiktok.com/v/...), НЕ на товары (shop.tiktok.com/view/product/...)
            if video_data["tiktok_link"] == "N/A":
                tiktok_link_selectors = [
                    'a[href*="m.tiktok.com/v/"]',  # Приоритет: ссылки на видео
                    'a[href*="tiktok.com/v/"]',    # Альтернативный формат
                    'a[href*="tiktok.com"]',       # Fallback
                ]
                
                for selector in tiktok_link_selectors:
                    try:
                        links = await self.page.query_selector_all(selector)
                        for link in links:
                            href = await link.get_attribute("href")
                            if href and "tiktok.com" in href:
                                # КРИТИЧНО: Пропускаем ссылки на товары в TikTok Shop
                                if "shop.tiktok.com/view/product" in href or "/view/product" in href:
                                    log.debug(f"      → Пропущена ссылка на товар: {href[:50]}...")
                                    continue
                                
                                # Берем только ссылки на видео (содержат /v/ в пути)
                                if "/v/" in href or "m.tiktok.com" in href:
                                    video_data["tiktok_link"] = href
                                    log.info(f"      ✅ TikTok ссылка найдена: {href[:50]}...")
                                    break
                        if video_data["tiktok_link"] != "N/A":
                            break
                    except:
                        continue
            
            if video_data["tiktok_link"] == "N/A":
                log.warning("      ⚠️ TikTok ссылка не найдена")
            
            # 2. Impressions - КРИТИЧНО: "Impressions" (англ.) или "Показы" (рус.), не "Likes" или "Нравится"!
            # Ищем в разделе "Data/Данные" в пункте "Impression/Показ"
            # Если не найдены на странице ad-search, используем из карточки (если есть)
            log.info("      → Извлечение impressions...")
            impression_text = await self._extract_impressions()
            if impression_text:
                # Сохраняем оригинальный формат (если он уже в формате "170.6K" или "339.9M")
                if impression_text.upper().endswith(('K', 'M')):
                    video_data["impression"] = impression_text
                    log.info(f"      ✅ Impressions (оригинальный формат): {impression_text}")
                else:
                    # Парсим число и форматируем обратно
                    impression_num = validator.parse_impressions(impression_text) or 0
                    video_data["impression"] = validator.format_impressions(impression_num)
                    log.info(f"      ✅ Impressions (сформатировано): {video_data['impression']}")
            else:
                # Если не найдены на странице ad-search, проверяем, есть ли они в исходных данных видео
                # (из карточки на странице товара)
                original_impression = video_data.get("_original_impression")
                if original_impression:
                    if isinstance(original_impression, (int, float)) and original_impression > 0:
                        video_data["impression"] = validator.format_impressions(int(original_impression))
                        log.info(f"      ✅ Impressions из карточки: {video_data['impression']}")
                    elif isinstance(original_impression, str) and original_impression != "N/A":
                        video_data["impression"] = original_impression
                        log.info(f"      ✅ Impressions из карточки (строка): {original_impression}")
                    else:
                        video_data["impression"] = "N/A"
                        log.warning("      ⚠️ Impressions не найдены ни на странице ad-search, ни в карточке")
                else:
                    video_data["impression"] = "N/A"
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
            
            # 4. Hook (из секции Hook или Hooks)
            log.info("      → Извлечение hook...")
            hook = await self._extract_hook()
            if not hook:
                # Повторный поиск, если не найден
                log.info("      → Hook не найден, повторный поиск...")
                hook = await self._extract_hook()
            
            if hook:
                video_data["hook"] = hook
                log.info(f"      ✅ Hook найден: {hook[:50]}...")
            else:
                video_data["hook"] = "N/A"
                log.info("      ⚠️ Hook не найден после повторного поиска, установлено 'N/A'")
            
            # 5. Audience Age (из поля Audience/Аудитория)
            log.info("      → Извлечение данных аудитории...")
            audience_data = await self._extract_audience()
            if audience_data:
                age = audience_data.get("age", "N/A")
                platform = audience_data.get("platform", "N/A")
                # Форматируем в формате "35-45" или "35-45 Android" (если есть платформа)
                # В строке 6 только возраст "25-35", без платформы
                video_data["audience_age"] = age if age != "N/A" else "N/A"
                log.info(f"      ✅ Audience: {video_data['audience_age']}")
            else:
                video_data["audience_age"] = "N/A"
                log.info("      ⚠️ Данные аудитории не найдены, установлено 'N/A'")
            
            # 6. Country (из поля "Country/Region" или "Страна/регион" - ОТДЕЛЬНО от Audience!)
            log.info("      → Извлечение страны...")
            country = await self._extract_country()
            if country:
                video_data["country"] = country
                log.info(f"      ✅ Country: {country}")
            else:
                video_data["country"] = "N/A"
                log.info("      ⚠️ Country не найден, установлено 'N/A'")
            
            # 7. First seen (формат "Oct 27 2025" - извлекаем только первую дату из "Oct 28 2025 ~ Nov 10 2025")
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
        Извлечь impressions - КРИТИЧНО: в разделе "Data/Данные" в пункте "Impression/Показ"
        ВАЖНО: НЕ брать шаблонные значения, только реальные данные со страницы!
        
        Returns:
            Строка с impressions (например "170.6K", "339.9M") или None
        """
        try:
            # Метод 1: Поиск через JavaScript по структуре DOM (более надежно)
            try:
                impression_data = await self.page.evaluate("""
                    () => {
                        // Ищем раздел "Data" или "Данные"
                        const dataKeywords = ['Data', 'Данные'];
                        const impressionKeywords = ['Impression', 'Показ', 'Показы'];
                        
                        // Ищем все элементы с текстом "Data" или "Данные"
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            const text = el.innerText || '';
                            
                            // Проверяем, содержит ли элемент "Data" или "Данные"
                            for (const dataKeyword of dataKeywords) {
                                if (text.includes(dataKeyword)) {
                                    // В этом разделе ищем "Impression" или "Показ"
                                    for (const impKeyword of impressionKeywords) {
                                        if (text.includes(impKeyword)) {
                                            // Ищем число в формате "170.6K", "403.2M" и т.д.
                                            const patterns = [
                                                new RegExp(impKeyword + '[\\s:]*([\\d.,]+[KM]?)', 'i'),
                                                new RegExp('([\\d.,]+[KM]?)\\s*' + impKeyword, 'i')
                                            ];
                                            
                                            for (const pattern of patterns) {
                                                const match = text.match(pattern);
                                                if (match && match[1]) {
                                                    const value = match[1];
                                                    // Проверяем, что это не слишком большое число (не шаблонное)
                                                    // Обычно реальные impressions от 50K до 500M
                                                    const numValue = parseFloat(value.replace(/[KM]/i, ''));
                                                    if (numValue >= 0.05 && numValue <= 1000) {
                                                        return value;
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Fallback: ищем напрямую "Impression" или "Показ" (НЕ "Likes"!)
                        for (const impKeyword of impressionKeywords) {
                            const elements = Array.from(document.querySelectorAll('*')).filter(el => {
                                const text = el.innerText || '';
                                return text.includes(impKeyword) && !text.toLowerCase().includes('likes') && !text.toLowerCase().includes('нравится');
                            });
                            
                            for (const el of elements) {
                                const text = el.innerText || '';
                                const patterns = [
                                    new RegExp(impKeyword + '[\\s:]*([\\d.,]+[KM]?)', 'i'),
                                    new RegExp('([\\d.,]+[KM]?)\\s*' + impKeyword, 'i')
                                ];
                                
                                for (const pattern of patterns) {
                                    const match = text.match(pattern);
                                    if (match && match[1]) {
                                        const value = match[1];
                                        const numValue = parseFloat(value.replace(/[KM]/i, ''));
                                        if (numValue >= 0.05 && numValue <= 1000) {
                                            return value;
                                        }
                                    }
                                }
                            }
                        }
                        
                        return null;
                    }
                """)
                
                if impression_data:
                    log.debug(f"Найдено impressions через JavaScript: {impression_data}")
                    return impression_data
            except Exception as e:
                log.debug(f"Ошибка при поиске impressions через JS: {e}")
            
            # Метод 2: Поиск через локаторы (fallback)
            data_keywords = ["Data", "Данные"]
            
            for keyword in data_keywords:
                try:
                    data_locator = self.page.locator(f'text=/{keyword}/i').first
                    if await data_locator.count() > 0:
                        impression_keywords = ["Impression", "Показ", "Показы"]
                        for imp_keyword in impression_keywords:
                            try:
                                parent_text = await data_locator.locator("..").inner_text()
                                if imp_keyword in parent_text and "Likes" not in parent_text and "Нравится" not in parent_text:
                                    pattern = rf'{imp_keyword}[:\s]*([\d.,]+[KM]?)'
                                    match = re.search(pattern, parent_text, re.IGNORECASE)
                                    if match:
                                        impression_str = match.group(1)
                                        # Проверяем, что это не шаблонное значение
                                        num_value = validator.parse_impressions(impression_str)
                                        if num_value and 50000 <= num_value <= 1000000000:  # От 50K до 1B
                                            log.debug(f"Найдено impressions в разделе Data: {impression_str}")
                                            return impression_str
                            except:
                                continue
                except:
                    continue
            
            log.warning("Не удалось найти 'Impression' или 'Показ' в разделе Data")
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении impressions: {e}")
            return None
    
    async def _extract_script(self) -> Optional[str]:
        """Извлечь сценарий из секции 'Script' или 'Сценарий' (или 'Transcript' или 'Анализ транскрипта')"""
        try:
            # Метод 1: Поиск через локаторы (английский и русский)
            script_keywords = ["Script", "Сценарий", "Transcript", "Анализ транскрипта", "Транскрипт"]
            
            for keyword in script_keywords:
                try:
                    # Ищем элемент с текстом
                    locator = self.page.locator(f'text=/{keyword}/i').first
                    if await locator.count() > 0:
                        # Способ 1: Текст родительского элемента
                        try:
                            parent_text = await locator.locator("..").inner_text()
                            if keyword in parent_text:
                                parts = parent_text.split(keyword, 1)
                                if len(parts) > 1:
                                    script = parts[1].strip()
                                    # Убираем лишние метки
                                    stop_words = ["Hook", "Хук", "Target Audience", "Целевая аудитория", 
                                                "First seen", "Впервые замечено", "Impressions", "Показы",
                                                "Limited Time Offer", "Annual Plan", "Promotion Period", "50% OFF",
                                                "Privacy", "Terms", "Copyright", "PIPIADS", "All Rights Reserved",
                                                "AI-agent", "cosmobeauty", "credits", "subscription", "invoice",
                                                "Monthly Credits", "Extra Credits", "data cost", "detail costs",
                                                "Team Setting", "Affiliate Dashboard", "Logout"]
                                    # Проверяем, что это не футер/меню
                                    footer_menu_keywords = ["Privacy", "Terms", "Copyright", "PIPIADS", "AI-agent", 
                                                           "cosmobeauty", "credits", "subscription", "invoice", 
                                                           "Monthly Credits", "Extra Credits", "@gmail.com"]
                                    is_footer_menu = any(keyword in script for keyword in footer_menu_keywords)
                                    
                                    for stop_word in stop_words:
                                        if stop_word in script:
                                            script = script.split(stop_word)[0].strip()
                                    # Фильтруем метаданные (Video Text Translator, Quality, Size и т.д.)
                                    metadata_keywords = ["Video Text Translator", "Translator", "Quality", "Size", "Resolution", 
                                                        "Width", "Height", "Duration", "Format", "Codec", "Frame Rate"]
                                    is_metadata = any(keyword in script for keyword in metadata_keywords)
                                    
                                    # Убираем теги (строки, начинающиеся с #) и служебные слова
                                    lines = script.split('\n')
                                    cleaned_lines = []
                                    skip_words = ['Tags', 'Script', 'Hooks', 'Tag', 'Hook']
                                    for line in lines:
                                        line = line.strip()
                                        # Пропускаем теги (начинаются с #), пустые строки и служебные слова
                                        if line and not line.startswith('#') and not any(skip in line for skip in skip_words):
                                            cleaned_lines.append(line)
                                    script = '\n'.join(cleaned_lines).strip()
                                    
                                    if script and len(script) > 10 and not is_footer_menu and not is_metadata:
                                        log.debug(f"Script найден через '{keyword}' (родитель)")
                                        return script
                        except:
                            pass
                        
                        # Способ 2: Текст следующего элемента
                        try:
                            next_sibling = await locator.evaluate_handle("el => el.nextElementSibling")
                            if next_sibling:
                                script = await next_sibling.as_element().inner_text()
                                # Проверяем, что это не футер/меню
                                footer_menu_keywords = ["Privacy", "Terms", "Copyright", "PIPIADS", "AI-agent", 
                                                       "cosmobeauty", "credits", "subscription", "invoice", 
                                                       "Monthly Credits", "Extra Credits", "@gmail.com"]
                                is_footer_menu = any(keyword in script for keyword in footer_menu_keywords)
                                # Фильтруем метаданные
                                metadata_keywords = ["Video Text Translator", "Translator", "Quality", "Size", "Resolution"]
                                is_metadata = any(keyword in script for keyword in metadata_keywords)
                                
                                # Убираем теги (строки, начинающиеся с #) и служебные слова
                                lines = script.split('\n')
                                cleaned_lines = []
                                skip_words = ['Tags', 'Script', 'Hooks', 'Tag', 'Hook']
                                for line in lines:
                                    line = line.strip()
                                    # Пропускаем теги (начинаются с #), пустые строки и служебные слова
                                    if line and not line.startswith('#') and not any(skip in line for skip in skip_words):
                                        cleaned_lines.append(line)
                                script = '\n'.join(cleaned_lines).strip()
                                
                                if script and len(script) > 10 and not is_footer_menu and not is_metadata:
                                    log.debug(f"Script найден через '{keyword}' (следующий элемент)")
                                    return script.strip()
                        except:
                            pass
                except:
                    continue
            
            # Метод 2: Поиск через JavaScript (более агрессивный - по структуре DOM)
            try:
                script = await self.page.evaluate("""
                    () => {
                        const keywords = ['Script', 'Сценарий', 'Transcript', 'Анализ транскрипта', 'Транскрипт'];
                        const stopWords = ['Hook', 'Хук', 'Target Audience', 'Целевая аудитория', 
                                          'First seen', 'Впервые замечено', 'Impressions', 'Показы',
                                          'Analysis', 'Advertiser', 'Display Name', 'Ad Copy',
                                          'Limited Time Offer', 'Annual Plan', 'Promotion Period', '50% OFF'];
                        
                        // Ищем элементы с ключевыми словами
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            const text = el.innerText || '';
                            
                            for (const keyword of keywords) {
                                if (text.includes(keyword)) {
                                    // Ищем следующий элемент после ключевого слова (обычно это сам script)
                                    let scriptText = null;
                                    
                                    // Способ 1: Текст следующего sibling элемента
                                    let nextSibling = el.nextElementSibling;
                                    if (nextSibling) {
                                        scriptText = nextSibling.innerText || '';
                                    }
                                    
                                    // Способ 2: Текст родительского элемента после ключевого слова
                                    if (!scriptText || scriptText.length < 10) {
                                        const parentText = el.parentElement ? el.parentElement.innerText || '' : '';
                                        if (parentText.includes(keyword)) {
                                            const parts = parentText.split(keyword);
                                            if (parts.length > 1) {
                                                scriptText = parts[1].trim();
                                            }
                                        }
                                    }
                                    
                                    // Способ 3: Ищем в дочерних элементах (обычно script в отдельном блоке)
                                    if (!scriptText || scriptText.length < 10) {
                                        const children = el.querySelectorAll('p, div, span');
                                        for (const child of children) {
                                            const childText = child.innerText || '';
                                            // Пропускаем метаданные и промо-тексты
                                            if (childText.length > 20 && 
                                                !childText.includes('Advertiser') && 
                                                !childText.includes('Display Name') &&
                                                !childText.includes('Analysis') &&
                                                !childText.includes('Generator') &&
                                                !childText.includes('Limited Time Offer') &&
                                                !childText.includes('Annual Plan') &&
                                                !childText.includes('Promotion Period') &&
                                                !childText.includes('50% OFF')) {
                                                scriptText = childText;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    if (scriptText) {
                                        // Убираем стоп-слова и метаданные
                                        for (const stopWord of stopWords) {
                                            if (scriptText.includes(stopWord)) {
                                                scriptText = scriptText.split(stopWord)[0];
                                            }
                                        }
                                        
                                        scriptText = scriptText.trim();
                                        
                                        // Убираем теги (строки, начинающиеся с #) и служебные слова
                                        const skipWords = ['Tags', 'Script', 'Hooks', 'Tag', 'Hook'];
                                        const lines = scriptText.split('\\n');
                                        const cleanedLines = [];
                                        for (const line of lines) {
                                            const trimmedLine = line.trim();
                                            // Пропускаем теги (начинаются с #), пустые строки и служебные слова
                                            if (trimmedLine && !trimmedLine.startsWith('#') && 
                                                !skipWords.some(word => trimmedLine.includes(word))) {
                                                cleanedLines.push(trimmedLine);
                                            }
                                        }
                                        scriptText = cleanedLines.join('\\n').trim();
                                        
                                        // Проверяем, что это похоже на реальный script (не метаданные, не промо-текст, не футер/меню)
                                        const footerMenuKeywords = ['Privacy', 'Terms', 'Copyright', 'PIPIADS', 'All Rights Reserved',
                                                                   'AI-agent', 'cosmobeauty', 'credits', 'subscription', 'invoice',
                                                                   'Monthly Credits', 'Extra Credits', 'data cost', 'detail costs',
                                                                   'Team Setting', 'Affiliate Dashboard', 'Logout', '@gmail.com',
                                                                   'English', 'Français', 'Deutsch', 'Español', 'Português'];
                                        const isFooterMenu = footerMenuKeywords.some(keyword => scriptText.includes(keyword));
                                        
                                        // Фильтруем короткие тексты и метаданные
                                    const metadataKeywords = ['Video Text Translator', 'Translator', 'Quality', 'Size', 'Resolution', 
                                                             'Width', 'Height', 'Duration', 'Format', 'Codec', 'Frame Rate'];
                                    const isMetadata = metadataKeywords.some(keyword => scriptText.includes(keyword));
                                    
                                    if (scriptText && scriptText.length > 20 && 
                                            !scriptText.startsWith('Analysis') &&
                                            !scriptText.includes('shop.tiktok.com') &&
                                            !scriptText.includes('Generator Image') &&
                                            !scriptText.includes('Limited Time Offer') &&
                                            !scriptText.includes('Annual Plan') &&
                                            !scriptText.includes('Promotion Period') &&
                                            !scriptText.includes('50% OFF') &&
                                            !scriptText.toLowerCase().includes('q4') &&
                                            !scriptText.toLowerCase().includes('monthly plan') &&
                                            !isFooterMenu &&
                                            !isMetadata) {
                                            return scriptText;
                                        }
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                if script and len(script) > 10:
                    log.debug("Script найден через JavaScript")
                    return script.strip()
            except Exception as e:
                log.debug(f"Ошибка при поиске script через JS: {e}")
            
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении сценария: {e}")
            return None
    
    async def _extract_hook(self) -> Optional[str]:
        """Извлечь hook из секции Hook/Hooks (англ.) или Хук/Хуки (рус.)
        ВАЖНО: Hook находится сразу после Script на странице!
        """
        try:
            # НОВЫЙ МЕТОД: Ищем Script, затем ищем Hook в следующем элементе/секции
            try:
                # Сначала находим Script
                script_keywords = ["Script", "Сценарий", "Transcript", "Анализ транскрипта"]
                for script_keyword in script_keywords:
                    try:
                        script_locator = self.page.locator(f'text=/{script_keyword}/i').first
                        if await script_locator.count() > 0:
                            # Ищем следующий элемент после Script, который содержит "Hook" или "Hooks"
                            # Или просто следующий текстовый блок после Script
                            try:
                                # Способ 1: Ищем элемент с "Hook" или "Hooks" после Script
                                parent = script_locator.locator("..")
                                parent_text = await parent.inner_text()
                                
                                # Ищем "Hook" или "Hooks" в том же родительском элементе
                                if "Hook" in parent_text or "Hooks" in parent_text or "Хук" in parent_text or "Хуки" in parent_text:
                                    # Находим позицию Script и Hook в тексте
                                    script_pos = parent_text.find(script_keyword)
                                    hook_pos = -1
                                    for hook_word in ["Hook", "Hooks", "Хук", "Хуки"]:
                                        pos = parent_text.find(hook_word, script_pos)
                                        if pos > script_pos:
                                            hook_pos = pos
                                            break
                                    
                                    if hook_pos > script_pos:
                                        # Извлекаем текст после "Hook" или "Hooks"
                                        hook_section = parent_text[hook_pos:]
                                        # Убираем "Hook" или "Hooks" из начала
                                        hook_section = re.sub(r'^Hooks?\s*:?\s*', '', hook_section, flags=re.IGNORECASE)
                                        hook_section = re.sub(r'^Хуки?\s*:?\s*', '', hook_section, flags=re.IGNORECASE)
                                        hook_text = hook_section.strip()
                                        
                                        # Убираем следующие секции (Target Audience, First seen и т.д.)
                                        stop_words = ["Target Audience", "Целевая аудитория", "First seen", "Впервые замечено", 
                                                    "Impressions", "Показы", "Country", "Страна", "Country/Region", "Страна/регион"]
                                        for stop_word in stop_words:
                                            if stop_word in hook_text:
                                                hook_text = hook_text.split(stop_word)[0].strip()
                                        
                                        # Убираем метаданные
                                        hook_text = re.sub(r'Quality\s*:?\s*[^\n]*', '', hook_text, flags=re.IGNORECASE)
                                        hook_text = re.sub(r'Size\s*:?\s*[^\n]*', '', hook_text, flags=re.IGNORECASE)
                                        hook_text = re.sub(r'Resolution\s*:?\s*[^\n]*', '', hook_text, flags=re.IGNORECASE)
                                        hook_text = re.sub(r'--', '', hook_text)
                                        hook_text = re.sub(r'\n{2,}', '\n', hook_text).strip()
                                        
                                        # Убираем служебные слова в начале
                                        hook_text = re.sub(r'^(Tags|Script|Hooks?)\s*:?\s*', '', hook_text, flags=re.IGNORECASE)
                                        
                                        if hook_text and len(hook_text) > 5 and len(hook_text) < 500:
                                            log.debug(f"Hook найден после Script через '{script_keyword}'")
                                            return hook_text
                            except:
                                pass
                            
                            # Способ 2: Ищем следующий sibling элемент после Script
                            try:
                                script_element = await script_locator.element_handle()
                                if script_element:
                                    # Ищем следующий элемент с текстом "Hook" или "Hooks"
                                    next_elements = await self.page.evaluate("""
                                        (scriptEl) => {
                                            let current = scriptEl;
                                            // Ищем следующий элемент с "Hook" или "Hooks"
                                            for (let i = 0; i < 10; i++) {
                                                current = current.nextElementSibling;
                                                if (!current) break;
                                                const text = current.innerText || '';
                                                if (text.includes('Hook') || text.includes('Hooks') || 
                                                    text.includes('Хук') || text.includes('Хуки')) {
                                                    // Извлекаем текст после "Hook" или "Hooks"
                                                    const parts = text.split(/Hooks?\\s*:?\\s*|Хуки?\\s*:?\\s*/i);
                                                    if (parts.length > 1) {
                                                        let hookText = parts[1].trim();
                                                        // Убираем следующие секции
                                                        const stopWords = ['Target Audience', 'First seen', 'Impressions', 'Country'];
                                                        for (const stop of stopWords) {
                                                            if (hookText.includes(stop)) {
                                                                hookText = hookText.split(stop)[0];
                                                            }
                                                        }
                                                        hookText = hookText.replace(/Quality\\s*:?\\s*[^\\n]*/gi, '');
                                                        hookText = hookText.replace(/Size\\s*:?\\s*[^\\n]*/gi, '');
                                                        hookText = hookText.replace(/Resolution\\s*:?\\s*[^\\n]*/gi, '');
                                                        hookText = hookText.replace(/--/g, '');
                                                        hookText = hookText.replace(/\\n{2,}/g, '\\n').trim();
                                                        if (hookText && hookText.length > 5 && hookText.length < 500) {
                                                            return hookText;
                                                        }
                                                    }
                                                }
                                            }
                                            return null;
                                        }
                                    """, script_element)
                                    
                                    if next_elements:
                                        log.debug(f"Hook найден в следующем элементе после Script")
                                        return next_elements
                            except:
                                pass
                            
                            # Способ 3: Ищем Hook в родительском контейнере после Script
                            try:
                                # Получаем весь текст страницы и ищем паттерн "Script...Hook"
                                page_text = await self.page.content()
                                # Ищем через JavaScript более агрессивно
                                hook_text = await self.page.evaluate("""
                                    () => {
                                        // Ищем все элементы с текстом "Script"
                                        const allElements = Array.from(document.querySelectorAll('*'));
                                        for (const el of allElements) {
                                            const text = el.innerText || '';
                                            if (text.includes('Script') || text.includes('Сценарий')) {
                                                // Ищем в этом же элементе или родительском "Hook" или "Hooks"
                                                let searchEl = el;
                                                for (let depth = 0; depth < 3; depth++) {
                                                    const searchText = searchEl.innerText || '';
                                                    if (searchText.includes('Hook') || searchText.includes('Hooks') || 
                                                        searchText.includes('Хук') || searchText.includes('Хуки')) {
                                                        // Извлекаем текст между Script и следующими секциями
                                                        const scriptIndex = searchText.indexOf('Script');
                                                        const hookIndex = searchText.indexOf('Hook', scriptIndex);
                                                        if (hookIndex > scriptIndex) {
                                                            let hookText = searchText.substring(hookIndex);
                                                            // Убираем "Hook" или "Hooks" из начала
                                                            hookText = hookText.replace(/^Hooks?\\s*:?\\s*/i, '');
                                                            hookText = hookText.replace(/^Хуки?\\s*:?\\s*/i, '');
                                                            // Убираем следующие секции
                                                            const stopWords = ['Target Audience', 'First seen', 'Impressions', 'Country'];
                                                            for (const stop of stopWords) {
                                                                if (hookText.includes(stop)) {
                                                                    hookText = hookText.split(stop)[0];
                                                                }
                                                            }
                                                            hookText = hookText.replace(/Quality\\s*:?\\s*[^\\n]*/gi, '');
                                                            hookText = hookText.replace(/Size\\s*:?\\s*[^\\n]*/gi, '');
                                                            hookText = hookText.replace(/Resolution\\s*:?\\s*[^\\n]*/gi, '');
                                                            hookText = hookText.replace(/--/g, '');
                                                            hookText = hookText.replace(/\\n{2,}/g, '\\n').trim();
                                                            if (hookText && hookText.length > 5 && hookText.length < 500) {
                                                                return hookText;
                                                            }
                                                        }
                                                    }
                                                    searchEl = searchEl.parentElement;
                                                    if (!searchEl) break;
                                                }
                                            }
                                        }
                                        return null;
                                    }
                                """)
                                
                                if hook_text:
                                    log.debug(f"Hook найден через агрессивный поиск после Script")
                                    return hook_text
                            except:
                                pass
                    except:
                        continue
            except:
                pass
            
            # Метод 1: Поиск через локаторы (старый способ, оставляем как fallback)
            hook_keywords = ["Hooks", "Hook", "Хуки", "Хук"]
            
            for keyword in hook_keywords:
                try:
                    locator = self.page.locator(f'text=/{keyword}/i').first
                    if await locator.count() > 0:
                        # Способ 1: Текст родительского элемента
                        try:
                            parent_text = await locator.locator("..").inner_text()
                            if keyword in parent_text:
                                parts = parent_text.split(keyword, 1)
                                if len(parts) > 1:
                                    hook = parts[1].strip()
                                    # Убираем лишние метки
                                    stop_words = ["Target Audience", "Целевая аудитория", "First seen", "Впервые замечено", 
                                                "Transcript", "Анализ транскрипта", "Impressions", "Показы",
                                                "Limited Time Offer", "Annual Plan", "Promotion Period", "50% OFF",
                                                "Privacy", "Terms", "Copyright", "PIPIADS", "All Rights Reserved",
                                                "AI-agent", "cosmobeauty", "credits", "subscription", "invoice",
                                                "Monthly Credits", "Extra Credits", "data cost", "detail costs",
                                                "Team Setting", "Affiliate Dashboard", "Logout"]
                                    # Проверяем, что это не футер/меню
                                    footer_menu_keywords = ["Privacy", "Terms", "Copyright", "PIPIADS", "AI-agent", 
                                                           "cosmobeauty", "credits", "subscription", "invoice", 
                                                           "Monthly Credits", "Extra Credits", "@gmail.com"]
                                    is_footer_menu = any(keyword in hook for keyword in footer_menu_keywords)
                                    
                                    for stop_word in stop_words:
                                        if stop_word in hook:
                                            hook = hook.split(stop_word)[0].strip()
                                    
                                    # Убираем метаданные видео (Quality, Size, Resolution и т.д.)
                                    metadata_patterns = [
                                        r'Quality\s*:?\s*[^\n]*',
                                        r'Size\s*:?\s*[^\n]*',
                                        r'Resolution\s*:?\s*[^\n]*',
                                        r'Width\s*:?\s*[^\n]*',
                                        r'Height\s*:?\s*[^\n]*',
                                        r'Duration\s*:?\s*[^\n]*',
                                        r'Format\s*:?\s*[^\n]*',
                                        r'Codec\s*:?\s*[^\n]*',
                                        r'Frame Rate\s*:?\s*[^\n]*',
                                        r'--',  # Убираем разделители "--"
                                    ]
                                    for pattern in metadata_patterns:
                                        hook = re.sub(pattern, '', hook, flags=re.IGNORECASE)
                                    hook = re.sub(r'\n{2,}', '\n', hook).strip()  # Убираем множественные переносы строк
                                    
                                    if hook and len(hook) > 5 and not is_footer_menu:
                                        log.debug(f"Hook найден через '{keyword}' (родитель)")
                                        return hook
                        except:
                            pass
                        
                        # Способ 2: Текст следующего элемента
                        try:
                            next_sibling = await locator.evaluate_handle("el => el.nextElementSibling")
                            if next_sibling:
                                hook = await next_sibling.as_element().inner_text()
                                # Проверяем, что это не футер/меню
                                footer_menu_keywords = ["Privacy", "Terms", "Copyright", "PIPIADS", "AI-agent", 
                                                       "cosmobeauty", "credits", "subscription", "invoice", 
                                                       "Monthly Credits", "Extra Credits", "@gmail.com"]
                                is_footer_menu = any(keyword in hook for keyword in footer_menu_keywords)
                                
                                # Убираем метаданные видео (Quality, Size, Resolution и т.д.)
                                metadata_patterns = [
                                    r'Quality\s*:?\s*[^\n]*',
                                    r'Size\s*:?\s*[^\n]*',
                                    r'Resolution\s*:?\s*[^\n]*',
                                    r'Width\s*:?\s*[^\n]*',
                                    r'Height\s*:?\s*[^\n]*',
                                    r'Duration\s*:?\s*[^\n]*',
                                    r'Format\s*:?\s*[^\n]*',
                                    r'Codec\s*:?\s*[^\n]*',
                                    r'Frame Rate\s*:?\s*[^\n]*',
                                    r'--',  # Убираем разделители "--"
                                ]
                                for pattern in metadata_patterns:
                                    hook = re.sub(pattern, '', hook, flags=re.IGNORECASE)
                                hook = re.sub(r'\n{2,}', '\n', hook).strip()  # Убираем множественные переносы строк
                                
                                if hook and len(hook) > 5 and not is_footer_menu:
                                    log.debug(f"Hook найден через '{keyword}' (следующий элемент)")
                                    return hook.strip()
                        except:
                            pass
                except:
                    continue
            
            # Метод 2: Поиск через JavaScript (более агрессивный - по структуре DOM)
            try:
                hook = await self.page.evaluate("""
                    () => {
                        const keywords = ['Hooks', 'Hook', 'Хуки', 'Хук'];
                        const stopWords = ['Target Audience', 'Целевая аудитория', 'First seen', 'Впервые замечено', 
                                         'Transcript', 'Анализ транскрипта', 'Impressions', 'Показы',
                                         'Script', 'Сценарий', 'Analysis',
                                         'Limited Time Offer', 'Annual Plan', 'Promotion Period', '50% OFF'];
                        
                        // Ищем элементы с ключевыми словами
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            const text = el.innerText || '';
                            
                            for (const keyword of keywords) {
                                if (text.includes(keyword)) {
                                    let hookText = null;
                                    
                                    // Способ 1: Текст следующего sibling элемента
                                    let nextSibling = el.nextElementSibling;
                                    if (nextSibling) {
                                        hookText = nextSibling.innerText || '';
                                    }
                                    
                                    // Способ 2: Текст родительского элемента после ключевого слова
                                    if (!hookText || hookText.length < 5) {
                                        const parentText = el.parentElement ? el.parentElement.innerText || '' : '';
                                        if (parentText.includes(keyword)) {
                                            const parts = parentText.split(keyword);
                                            if (parts.length > 1) {
                                                hookText = parts[1].trim();
                                            }
                                        }
                                    }
                                    
                                    // Способ 3: Ищем в дочерних элементах
                                    if (!hookText || hookText.length < 5) {
                                        const children = el.querySelectorAll('p, div, span');
                                        for (const child of children) {
                                            const childText = child.innerText || '';
                                            if (childText.length > 5 && childText.length < 200) {
                                                hookText = childText;
                                                break;
                                            }
                                        }
                                    }
                                    
                                    if (hookText) {
                                        // Убираем стоп-слова
                                        for (const stopWord of stopWords) {
                                            if (hookText.includes(stopWord)) {
                                                hookText = hookText.split(stopWord)[0];
                                            }
                                        }
                                        
                                        hookText = hookText.trim();
                                        
                                        // Проверяем, что это похоже на реальный hook (короткая фраза, не промо-текст, не футер/меню)
                                        const footerMenuKeywords = ['Privacy', 'Terms', 'Copyright', 'PIPIADS', 'All Rights Reserved',
                                                                   'AI-agent', 'cosmobeauty', 'credits', 'subscription', 'invoice',
                                                                   'Monthly Credits', 'Extra Credits', 'data cost', 'detail costs',
                                                                   'Team Setting', 'Affiliate Dashboard', 'Logout', '@gmail.com',
                                                                   'English', 'Français', 'Deutsch', 'Español', 'Português'];
                                        const isFooterMenu = footerMenuKeywords.some(keyword => hookText.includes(keyword));
                                        
                                        // Убираем метаданные видео (Quality, Size, Resolution и т.д.)
                                        const metadataPatterns = [
                                            /Quality\s*:?\s*[^\n]*/gi,
                                            /Size\s*:?\s*[^\n]*/gi,
                                            /Resolution\s*:?\s*[^\n]*/gi,
                                            /Width\s*:?\s*[^\n]*/gi,
                                            /Height\s*:?\s*[^\n]*/gi,
                                            /Duration\s*:?\s*[^\n]*/gi,
                                            /Format\s*:?\s*[^\n]*/gi,
                                            /Codec\s*:?\s*[^\n]*/gi,
                                            /Frame Rate\s*:?\s*[^\n]*/gi,
                                            /--/g,  // Убираем разделители "--"
                                        ];
                                        let cleanedHook = hookText;
                                        for (const pattern of metadataPatterns) {
                                            cleanedHook = cleanedHook.replace(pattern, '');
                                        }
                                        cleanedHook = cleanedHook.replace(/\n{2,}/g, '\n').trim();  // Убираем множественные переносы строк
                                        
                                        if (cleanedHook && cleanedHook.length > 5 && cleanedHook.length < 300 &&
                                            !cleanedHook.includes('Limited Time Offer') &&
                                            !cleanedHook.includes('Annual Plan') &&
                                            !cleanedHook.includes('Promotion Period') &&
                                            !cleanedHook.includes('50% OFF') &&
                                            !cleanedHook.toLowerCase().includes('q4') &&
                                            !cleanedHook.toLowerCase().includes('monthly plan') &&
                                            !isFooterMenu) {
                                            return cleanedHook;
                                        }
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                if hook and len(hook) > 5:
                    log.debug("Hook найден через JavaScript")
                    return hook.strip()
            except Exception as e:
                log.debug(f"Ошибка при поиске hook через JS: {e}")
            
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении hook: {e}")
            return None
    
    async def _extract_audience(self) -> Optional[Dict[str, str]]:
        """Извлечь возраст и платформу из поля Audience/Аудитория в формате 'Аудитория: Возраст: 25-35 | Устройство: Android'"""
        try:
            audience_data = {"age": "N/A", "platform": "N/A"}
            
            # Метод 1: Поиск через локаторы
            audience_keywords = ["Audience", "Аудитория", "Target Audience", "Целевая аудитория"]
            
            for keyword in audience_keywords:
                try:
                    locator = self.page.locator(f'text=/{keyword}/i').first
                    if await locator.count() > 0:
                        # Ищем текст аудитории рядом
                        text = await locator.locator("..").inner_text()
                        
                        # Ищем возраст в формате "Возраст: 25-35" или просто "25-35"
                        age_patterns = [
                            r'Возраст[:\s]+(\d{1,2}-\d{1,2})',
                            r'Age[:\s]+(\d{1,2}-\d{1,2})',
                            r'(\d{1,2}-\d{1,2})',  # Просто возраст
                        ]
                        
                        for pattern in age_patterns:
                            age_match = re.search(pattern, text, re.IGNORECASE)
                            if age_match:
                                audience_data["age"] = age_match.group(1)
                                break
                        
                        # Ищем платформу в формате "Устройство: Android" или "| Android"
                        platform_patterns = [
                            r'Устройство[:\s]+(Android|iOS)',
                            r'Device[:\s]+(Android|iOS)',
                            r'\|\s*(Android|iOS)',
                            r'(Android|iOS)',
                        ]
                        
                        for pattern in platform_patterns:
                            platform_match = re.search(pattern, text, re.IGNORECASE)
                            if platform_match:
                                platform = platform_match.group(1)
                                if platform.lower() in ["ios", "iphone", "ipad"]:
                                    audience_data["platform"] = "iOS"
                                else:
                                    audience_data["platform"] = "Android"
                                break
                        
                        if audience_data["age"] != "N/A" or audience_data["platform"] != "N/A":
                            return audience_data
                except:
                    continue
            
            # Метод 2: Поиск через JavaScript (более агрессивный)
            try:
                result = await self.page.evaluate("""
                    () => {
                        const keywords = ['Target Audience', 'Целевая аудитория', 'Audience', 'Аудитория'];
                        const agePattern = /(\\d{1,2}-\\d{1,2})/;
                        const platformKeywords = ['Android', 'iOS', 'iPhone', 'iPad'];
                        const countryKeywords = ['USA', 'US', 'United States', 'Россия', 'Russia', 'Philippines', 
                                                'Филиппины', 'China', 'Китай', 'India', 'Индия'];
                        
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            const text = el.innerText || '';
                            
                            for (const keyword of keywords) {
                                if (text.includes(keyword)) {
                                    const result = {age: 'N/A', platform: 'N/A', country: 'N/A'};
                                    
                                    // Ищем возраст
                                    const ageMatch = text.match(agePattern);
                                    if (ageMatch) {
                                        result.age = ageMatch[1];
                                    }
                                    
                                    // Ищем платформу
                                    for (const platform of platformKeywords) {
                                        if (text.includes(platform)) {
                                            result.platform = (platform === 'iOS' || platform === 'iPhone' || platform === 'iPad') ? 'iOS' : 'Android';
                                            break;
                                        }
                                    }
                                    
                                    // Ищем страну
                                    for (const country of countryKeywords) {
                                        if (text.includes(country)) {
                                            result.country = country;
                                            break;
                                        }
                                    }
                                    
                                    if (result.age !== 'N/A' || result.platform !== 'N/A' || result.country !== 'N/A') {
                                        return result;
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                if result:
                    audience_data.update(result)
                    return audience_data
            except Exception as e:
                log.debug(f"Ошибка при поиске audience через JS: {e}")
            
            return audience_data
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении аудитории: {e}")
            return None
    
    async def _extract_country(self) -> Optional[str]:
        """Извлечь страну из поля 'Country/Region' или 'Страна/регион' (ОТДЕЛЬНО от Audience!)"""
        try:
            country_keywords = ["Country/Region", "Страна/регион", "Country", "Страна", "Region", "Регион"]
            
            for keyword in country_keywords:
                try:
                    locator = self.page.locator(f'text=/{keyword}/i').first
                    if await locator.count() > 0:
                        # Ищем текст страны рядом
                        text = await locator.locator("..").inner_text()
                        
                        # Ищем страну (расширенный список)
                        country_patterns = [
                            r'United States(?:\([0-9]+\))?',  # United States(1)
                            r'USA(?:\([0-9]+\))?',
                            r'US(?:\([0-9]+\))?',
                            r'Philippines(?:\([0-9]+\))?',
                            r'Филиппины(?:\([0-9]+\))?',
                            r'Russia(?:\([0-9]+\))?',
                            r'Россия(?:\([0-9]+\))?',
                            r'China(?:\([0-9]+\))?',
                            r'Китай(?:\([0-9]+\))?',
                            r'India(?:\([0-9]+\))?',
                            r'Индия(?:\([0-9]+\))?',
                            r'Brazil(?:\([0-9]+\))?',
                            r'Бразилия(?:\([0-9]+\))?',
                            r'Germany(?:\([0-9]+\))?',
                            r'Германия(?:\([0-9]+\))?',
                            r'France(?:\([0-9]+\))?',
                            r'Франция(?:\([0-9]+\))?',
                            r'UK(?:\([0-9]+\))?',
                            r'United Kingdom(?:\([0-9]+\))?',
                        ]
                        
                        for pattern in country_patterns:
                            match = re.search(pattern, text, re.IGNORECASE)
                            if match:
                                country = match.group(0)
                                # Убираем (1) и т.д.
                                country = re.sub(r'\([0-9]+\)', '', country).strip()
                                log.debug(f"Country найден через '{keyword}': {country}")
                                return country
                except:
                    continue
            
            # Метод 2: Поиск через JavaScript
            try:
                country = await self.page.evaluate("""
                    () => {
                        const keywords = ['Country/Region', 'Страна/регион', 'Country', 'Страна'];
                        const countryPatterns = [
                            /United States(?:\\([0-9]+\\))?/i,
                            /USA(?:\\([0-9]+\\))?/i,
                            /Philippines(?:\\([0-9]+\\))?/i,
                            /Russia(?:\\([0-9]+\\))?/i,
                            /China(?:\\([0-9]+\\))?/i,
                            /India(?:\\([0-9]+\\))?/i
                        ];
                        
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            const text = el.innerText || '';
                            
                            for (const keyword of keywords) {
                                if (text.includes(keyword)) {
                                    for (const pattern of countryPatterns) {
                                        const match = text.match(pattern);
                                        if (match) {
                                            return match[0].replace(/\\([0-9]+\\)/g, '').trim();
                                        }
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                if country:
                    log.debug(f"Country найден через JavaScript: {country}")
                    return country.strip()
            except Exception as e:
                log.debug(f"Ошибка при поиске country через JS: {e}")
            
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении country: {e}")
            return None
    
    async def _extract_first_seen(self) -> Optional[str]:
        """Извлечь First seen в формате 'Oct 27 2025' - только первую дату из 'Oct 28 2025 ~ Nov 10 2025'"""
        try:
            # Метод 1: Поиск через локаторы
            first_seen_keywords = ["First seen - Last seen", "First seen", "Впервые замечено", "First Seen"]
            
            for keyword in first_seen_keywords:
                try:
                    locator = self.page.locator(f'text=/{keyword}/i').first
                    if await locator.count() > 0:
                        # Ищем текст даты рядом
                        text = await locator.locator("..").inner_text()
                        
                        # Ищем дату в формате "Oct 27 2025" или "Oct 27, 2025"
                        # Ищем первую дату из диапазона "Oct 28 2025 ~ Nov 10 2025"
                        date_patterns = [
                            r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})',  # Oct 27 2025
                            r'([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})',  # Oct 27, 2025
                            r'(\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4})',  # 27 Oct 2025
                        ]
                        
                        for pattern in date_patterns:
                            # Ищем первую дату (до ~ или конца строки)
                            date_match = re.search(pattern, text)
                            if date_match:
                                date_str = date_match.group(1)
                                # Нормализуем формат (убираем запятую если есть)
                                date_str = date_str.replace(',', '').strip()
                                log.debug(f"First seen найден через '{keyword}': {date_str}")
                                return date_str
                        
                        # Также пробуем найти дату после ключевых слов
                        if keyword in text:
                            parts = text.split(keyword, 1)
                            if len(parts) > 1:
                                # Берем только до ~ (если есть диапазон)
                                after_keyword = parts[1].split('~')[0].strip()
                                for pattern in date_patterns:
                                    date_match = re.search(pattern, after_keyword)
                                    if date_match:
                                        date_str = date_match.group(1).replace(',', '').strip()
                                        log.debug(f"First seen найден после '{keyword}': {date_str}")
                                        return date_str
                except:
                    continue
            
            # Метод 2: Поиск через JavaScript (более агрессивный - по структуре DOM)
            try:
                first_seen = await self.page.evaluate("""
                    () => {
                        const keywords = ['First seen - Last seen', 'First seen', 'Впервые замечено', 'First Seen'];
                        const datePatterns = [
                            /([A-Z][a-z]{2}\\s+\\d{1,2}\\s+\\d{4})/,  // Oct 27 2025
                            /([A-Z][a-z]{2}\\s+\\d{1,2},\\s+\\d{4})/,  // Oct 27, 2025
                            /(\\d{1,2}\\s+[A-Z][a-z]{2}\\s+\\d{4})/   // 27 Oct 2025
                        ];
                        
                        const allElements = document.querySelectorAll('*');
                        for (const el of allElements) {
                            const text = el.innerText || '';
                            
                            for (const keyword of keywords) {
                                if (text.includes(keyword)) {
                                    // Ищем дату после ключевого слова
                                    const index = text.indexOf(keyword);
                                    let afterKeyword = text.substring(index + keyword.length);
                                    
                                    // Берем только до ~ (если есть диапазон)
                                    if (afterKeyword.includes('~')) {
                                        afterKeyword = afterKeyword.split('~')[0];
                                    }
                                    
                                    for (const pattern of datePatterns) {
                                        const match = afterKeyword.match(pattern);
                                        if (match) {
                                            const dateStr = match[1].replace(',', '').trim();
                                            // Возвращаем первую найденную дату (без проверок - фильтрация будет в _filter_videos)
                                            return dateStr;
                                        }
                                    }
                                }
                            }
                        }
                        return null;
                    }
                """)
                if first_seen:
                    log.debug(f"First seen найден через JavaScript: {first_seen}")
                    return first_seen.strip()
            except Exception as e:
                log.debug(f"Ошибка при поиске first_seen через JS: {e}")
            
            return None
            
        except Exception as e:
            log.debug(f"Ошибка при извлечении first_seen: {e}")
            return None

