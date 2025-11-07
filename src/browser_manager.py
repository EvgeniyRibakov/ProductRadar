"""
Browser Manager - управление браузером с защитой от блокировок
"""

import asyncio
import json
import random
import time
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, TimeoutError as PlaywrightTimeoutError

from . import config
from . import logger

# Глобальный логгер
log = logger.get_logger("BrowserManager")

# User agents для ротации
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Путь для сохранения cookies
COOKIES_FILE = config.CONFIG_DIR / "cookies.json"


class BrowserManager:
    """Управление браузером с защитой от блокировок"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None
        
    async def initialize(self, headless: Optional[bool] = None) -> bool:
        """
        Инициализация браузера с защитой от блокировок
        
        Args:
            headless: Headless режим (если None, берется из config)
        
        Returns:
            True если успешно
        """
        try:
            log.info("Инициализация Playwright...")
            
            self.playwright = await async_playwright().start()
            
            # Выбор headless режима
            if headless is None:
                headless = config.BROWSER_HEADLESS
            
            # Случайный user agent
            user_agent = random.choice(USER_AGENTS)
            log.debug(f"Используется user agent: {user_agent[:50]}...")
            
            # Запуск браузера с реалистичными параметрами
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                ]
            )
            
            # Создание контекста с реалистичными параметрами
            self.context = await self.browser.new_context(
                user_agent=user_agent,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",  # Английский язык для оригинальной версии сайта
                timezone_id="America/New_York",  # США
                permissions=["geolocation"],
                geolocation={"latitude": 40.7128, "longitude": -74.0060},  # Нью-Йорк
                color_scheme="light",
                # Отключаем автоматизацию
                java_script_enabled=True,
                bypass_csp=True,
            )
            
            # Добавляем скрипты для скрытия автоматизации
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                window.chrome = {
                    runtime: {}
                };
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
                
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
            """)
            
            # Создание страницы
            self.page = await self.context.new_page()
            
            log.info("✅ Браузер инициализирован")
            return True
            
        except Exception as e:
            log.error(f"Ошибка инициализации браузера: {e}")
            return False
    
    async def human_delay(self, min_seconds: Optional[float] = None, max_seconds: Optional[float] = None):
        """
        Имитация человеческой задержки (random delay)
        
        Args:
            min_seconds: Минимальная задержка (из config если None)
            max_seconds: Максимальная задержка (из config если None)
        """
        if min_seconds is None:
            min_seconds = config.RANDOM_DELAY_MIN
        if max_seconds is None:
            max_seconds = config.RANDOM_DELAY_MAX
        
        delay = random.uniform(min_seconds, max_seconds)
        log.debug(f"Задержка {delay:.2f} секунд (имитация человека)")
        await asyncio.sleep(delay)
    
    async def load_cookies(self) -> bool:
        """
        Загрузка сохраненных cookies
        
        Returns:
            True если cookies загружены
        """
        if not COOKIES_FILE.exists():
            log.info("Файл cookies не найден, пропуск загрузки")
            return False
        
        try:
            with open(COOKIES_FILE, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            if self.context and cookies:
                await self.context.add_cookies(cookies)
                log.info(f"✅ Загружено {len(cookies)} cookies")
                return True
        except Exception as e:
            log.warning(f"Ошибка загрузки cookies: {e}")
        
        return False
    
    async def save_cookies(self) -> bool:
        """
        Сохранение cookies
        
        Returns:
            True если cookies сохранены
        """
        if not self.context:
            return False
        
        try:
            cookies = await self.context.cookies()
            with open(COOKIES_FILE, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            log.info(f"✅ Сохранено {len(cookies)} cookies")
            return True
        except Exception as e:
            log.error(f"Ошибка сохранения cookies: {e}")
            return False
    
    async def navigate_with_retry(
        self,
        url: str,
        max_retries: int = None,
        wait_until: str = "networkidle",
        timeout: int = None
    ) -> bool:
        """
        Навигация с retry и обработкой блокировок
        
        Args:
            url: URL для загрузки
            max_retries: Максимальное количество попыток
            wait_until: Когда считать загрузку завершенной
            timeout: Таймаут в миллисекундах
        
        Returns:
            True если успешно
        """
        if max_retries is None:
            max_retries = config.MAX_RETRIES
        if timeout is None:
            timeout = config.BROWSER_TIMEOUT
        
        if not self.page:
            log.error("Страница не инициализирована")
            return False
        
        for attempt in range(max_retries):
            try:
                log.info(f"Переход на {url} (попытка {attempt + 1}/{max_retries})")
                
                # Человеческая задержка перед навигацией
                await self.human_delay()
                
                response = await self.page.goto(
                    url,
                    wait_until=wait_until,
                    timeout=timeout
                )
                
                # Проверка на блокировки
                if response:
                    status = response.status
                    if status == 429:  # Too Many Requests
                        log.warning(f"Получен 429 (Too Many Requests), ожидание...")
                        delay = config.RETRY_DELAY_BASE * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    elif status == 403:  # Forbidden
                        log.error(f"Получен 403 (Forbidden) - возможна блокировка")
                        # Можно добавить более сложную обработку
                        delay = config.RETRY_DELAY_BASE * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                    elif status >= 400:
                        log.warning(f"Получен статус {status}, повторная попытка...")
                        delay = config.RETRY_DELAY_BASE * (2 ** attempt)
                        await asyncio.sleep(delay)
                        continue
                
                # Проверка на каптч
                if await self._check_captcha():
                    log.error("Обнаружена каптч! Требуется ручное вмешательство")
                    # Можно добавить паузу и уведомление
                    await asyncio.sleep(60)  # Пауза 1 минута
                    continue
                
                log.info(f"✅ Страница загружена успешно")
                return True
                
            except PlaywrightTimeoutError:
                log.warning(f"Таймаут при загрузке (попытка {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    delay = config.RETRY_DELAY_BASE * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    log.error("Превышено максимальное количество попыток")
                    return False
                    
            except Exception as e:
                log.error(f"Ошибка при навигации: {e}")
                if attempt < max_retries - 1:
                    delay = config.RETRY_DELAY_BASE * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    return False
        
        return False
    
    async def _check_captcha(self) -> bool:
        """
        Проверка наличия каптч на странице
        
        Returns:
            True если каптч обнаружена
        """
        if not self.page:
            return False
        
        try:
            # Проверка различных индикаторов каптч
            captcha_indicators = [
                "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']",
                ".g-recaptcha",
                "[data-sitekey]",
                "text=Please verify you are human",
                "text=Подтвердите, что вы не робот",
            ]
            
            for selector in captcha_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        log.warning(f"Обнаружена каптч: {selector}")
                        return True
                except:
                    continue
            
            # Проверка по тексту на странице
            page_text = await self.page.content()
            captcha_keywords = [
                "recaptcha",
                "hcaptcha",
                "verify you are human",
                "подтвердите что вы не робот",
                "captcha",
            ]
            
            page_text_lower = page_text.lower()
            for keyword in captcha_keywords:
                if keyword in page_text_lower:
                    log.warning(f"Обнаружено ключевое слово каптч: {keyword}")
                    return True
            
            return False
            
        except Exception as e:
            log.debug(f"Ошибка при проверке каптч: {e}")
            return False
    
    async def login_to_pipiads(self) -> bool:
        """
        Авторизация на Pipiads
        
        Returns:
            True если авторизация успешна
        """
        if not self.page:
            log.error("Страница не инициализирована")
            return False
        
        try:
            log.info("Начало авторизации на Pipiads...")
            
            # Загрузка начальной страницы
            if not await self.navigate_with_retry(config.PIPIADS_INITIAL_URL):
                log.error("Не удалось загрузить начальную страницу")
                return False
            
            await self.human_delay(2, 4)
            
            # Проверка, авторизованы ли уже (более строгая проверка)
            current_url = self.page.url
            log.debug(f"Текущий URL: {current_url}")
            
            # Если URL содержит /login, значит точно не авторизован
            if "/login" in current_url.lower():
                log.info("Обнаружена страница входа, требуется авторизация")
            # Если перенаправлены на страницу входа, ждем загрузки
            elif "login" in current_url.lower():
                log.info("Перенаправление на страницу входа...")
                await self.human_delay(2, 3)
            elif await self._check_logged_in_strict():
                log.info("✅ Уже авторизован (cookies работают)")
                return True
            else:
                log.info("Проверка авторизации...")
                # Проверяем, есть ли форма входа на странице
                login_form = await self.page.query_selector('input[type="email"], input[placeholder*="почт"], input[placeholder*="email"]')
                if login_form:
                    log.info("Обнаружена форма входа на странице")
                else:
                    # Если нет формы входа, возможно уже авторизован
                    if await self._check_logged_in_strict():
                        log.info("✅ Уже авторизован")
                        return True
                    else:
                        log.warning("Не удалось определить статус авторизации, пробуем войти")
            
            # Поиск полей входа - более точные селекторы
            log.info("Поиск полей для входа...")
            
            # Ждем загрузки страницы
            await self.page.wait_for_load_state("domcontentloaded")
            await self.human_delay(1, 2)
            
            # Пробуем разные варианты селекторов
            email_selectors = [
                'input[type="email"]',
                'input[name="email"]',
                'input[placeholder*="почт"]',
                'input[placeholder*="email"]',
                'input[placeholder*="Электронная почта"]',
                'label:has-text("Электронная почта") + input',
                'input[aria-label*="почт"]',
            ]
            
            password_selectors = [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="парол"]',
                'input[placeholder*="Пароль"]',
                'label:has-text("Пароль") + input',
            ]
            
            email_field = None
            password_field = None
            
            # Пробуем найти поле email с ожиданием
            for selector in email_selectors:
                try:
                    # Сначала пробуем подождать появления элемента
                    try:
                        await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                    except:
                        pass
                    
                    email_field = await self.page.query_selector(selector)
                    if email_field:
                        is_visible = await email_field.is_visible()
                        if is_visible:
                            log.debug(f"Найдено поле email: {selector}")
                            break
                        else:
                            email_field = None
                except Exception as e:
                    log.debug(f"Ошибка при поиске email поля {selector}: {e}")
                    continue
            
            # Пробуем найти поле password с ожиданием
            for selector in password_selectors:
                try:
                    try:
                        await self.page.wait_for_selector(selector, timeout=3000, state="visible")
                    except:
                        pass
                    
                    password_field = await self.page.query_selector(selector)
                    if password_field:
                        is_visible = await password_field.is_visible()
                        if is_visible:
                            log.debug(f"Найдено поле password: {selector}")
                            break
                        else:
                            password_field = None
                except Exception as e:
                    log.debug(f"Ошибка при поиске password поля {selector}: {e}")
                    continue
            
            if not email_field:
                log.error("❌ Не найдено поле для email")
                # Сохраняем скриншот для отладки
                await self.page.screenshot(path=str(config.SCREENSHOTS_DIR / f"login_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"))
                return False
            
            if not password_field:
                log.error("❌ Не найдено поле для пароля")
                await self.page.screenshot(path=str(config.SCREENSHOTS_DIR / f"login_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"))
                return False
            
            log.info("✅ Поля для входа найдены")
            
            # Ввод email
            log.info("Ввод email...")
            await email_field.scroll_into_view_if_needed()
            await self.human_delay(0.5, 1)
            await email_field.click()
            await self.human_delay(0.5, 1)
            # Очищаем поле через fill("") и затем вводим значение
            await email_field.fill("")  # Очищаем поле
            await self.human_delay(0.3, 0.7)
            await email_field.fill(config.PIPIADS_EMAIL)
            await self.human_delay(0.5, 1)
            log.debug(f"Email введен: {config.PIPIADS_EMAIL}")
            
            # Ввод пароля
            log.info("Ввод пароля...")
            await password_field.scroll_into_view_if_needed()
            await self.human_delay(0.5, 1)
            await password_field.click()
            await self.human_delay(0.5, 1)
            await password_field.fill("")  # Очищаем поле
            await self.human_delay(0.3, 0.7)
            await password_field.fill(config.PIPIADS_PASSWORD)
            await self.human_delay(1, 2)
            log.debug("Пароль введен")
            
            # Поиск кнопки входа
            log.info("Поиск кнопки входа...")
            login_button_selectors = [
                'button:has-text("Войти")',
                'button:has-text("Login")',
                'button[type="submit"]',
                'form button[type="submit"]',
                'button.btn-primary',
                'button.btn-login',
                'input[type="submit"]',
            ]
            
            login_button = None
            for selector in login_button_selectors:
                try:
                    login_button = await self.page.query_selector(selector)
                    if login_button:
                        is_visible = await login_button.is_visible()
                        if is_visible:
                            log.debug(f"Найдена кнопка входа: {selector}")
                            break
                        else:
                            login_button = None
                except Exception as e:
                    log.debug(f"Ошибка при поиске кнопки {selector}: {e}")
                    continue
            
            # Нажатие кнопки входа или Enter
            if login_button:
                log.info("Нажатие кнопки входа...")
                await login_button.scroll_into_view_if_needed()
                await self.human_delay(0.5, 1)
                await login_button.click()
            else:
                log.info("Кнопка не найдена, нажимаем Enter...")
                await password_field.press("Enter")
            
            # Ожидание загрузки после входа
            log.info("Ожидание завершения авторизации...")
            await self.human_delay(3, 5)
            
            # Ждем, пока страница перезагрузится или изменится URL
            try:
                await self.page.wait_for_load_state("networkidle", timeout=10000)
            except:
                pass
            
            await self.human_delay(2, 3)
            
            # Проверка успешности входа
            if await self._check_logged_in_strict():
                log.info("✅ Авторизация успешна")
                await self.save_cookies()
                return True
            else:
                log.error("❌ Авторизация не удалась - проверка авторизации не прошла")
                # Сохраняем скриншот для отладки
                await self.page.screenshot(path=str(config.SCREENSHOTS_DIR / f"login_failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"))
                return False
                
        except Exception as e:
            log.error(f"Ошибка при авторизации: {e}")
            import traceback
            log.error(traceback.format_exc())
            # Сохраняем скриншот при ошибке
            try:
                await self.page.screenshot(path=str(config.SCREENSHOTS_DIR / f"login_exception_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"))
            except:
                pass
            return False
    
    async def _check_logged_in_strict(self) -> bool:
        """
        Строгая проверка, авторизован ли пользователь
        
        Returns:
            True если авторизован
        """
        if not self.page:
            return False
        
        try:
            current_url = self.page.url
            log.debug(f"Проверка авторизации, URL: {current_url}")
            
            # Если URL содержит /login, точно не авторизован
            if "/login" in current_url.lower():
                log.debug("URL содержит /login - не авторизован")
                return False
            
            # Проверка наличия формы входа на странице
            login_form_indicators = [
                'input[type="email"]',
                'input[placeholder*="почт"]',
                'input[placeholder*="email"]',
                'text=Войти',
                'text=Login',
            ]
            
            for selector in login_form_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        # Проверяем, видима ли форма
                        is_visible = await element.is_visible()
                        if is_visible:
                            log.debug(f"Обнаружена форма входа: {selector}")
                            return False
                except:
                    continue
            
            # Проверка индикаторов авторизации (должны быть видны)
            logged_in_indicators = [
                'a[href*="logout"]',
                'button:has-text("Выйти")',
                'button:has-text("Logout")',
                '.user-menu',
                '.profile',
                '[class*="user"]',
                '[class*="profile"]',
            ]
            
            found_indicators = 0
            for selector in logged_in_indicators:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        is_visible = await element.is_visible()
                        if is_visible:
                            found_indicators += 1
                            log.debug(f"Найден индикатор авторизации: {selector}")
                except:
                    continue
            
            # Если найдено хотя бы 2 индикатора авторизации, считаем авторизованным
            if found_indicators >= 1:
                log.debug(f"Найдено {found_indicators} индикаторов авторизации")
                return True
            
            # Дополнительная проверка: если на странице есть товары или контент, требующий авторизации
            # и нет формы входа, возможно авторизован
            page_content = await self.page.content()
            if "tiktok-shop-product" in current_url and "login" not in current_url.lower():
                # Если мы на странице товаров и нет формы входа, возможно авторизован
                if "input[type='email']" not in page_content.lower():
                    log.debug("На странице товаров, форма входа не найдена - возможно авторизован")
                    return True
            
            log.debug("Не найдено достаточных индикаторов авторизации")
            return False
            
        except Exception as e:
            log.debug(f"Ошибка при проверке авторизации: {e}")
            return False
    
    async def _check_logged_in(self) -> bool:
        """
        Проверка, авторизован ли пользователь (старая версия для совместимости)
        
        Returns:
            True если авторизован
        """
        return await self._check_logged_in_strict()
    
    async def close(self):
        """Закрытие браузера"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            log.info("Браузер закрыт")
        except Exception as e:
            log.error(f"Ошибка при закрытии браузера: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        await self.load_cookies()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.save_cookies()
        await self.close()

