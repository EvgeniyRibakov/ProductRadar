"""Базовый парсер для всех платформ"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import aiohttp
from bs4 import BeautifulSoup

from src.models.product import Product
from src.utils.logger import setup_logger


class BaseParser(ABC):
    """Базовый класс для парсеров платформ"""
    
    def __init__(self, platform_name: str):
        """
        Инициализация парсера
        
        Args:
            platform_name: Название платформы
        """
        self.platform_name = platform_name
        self.logger = setup_logger(f"{__name__}.{platform_name}")
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Вход в контекстный менеджер"""
        await self.init_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера"""
        await self.close_session()
    
    async def init_session(self) -> None:
        """Инициализация HTTP сессии"""
        if not self.session:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
            self.logger.info(f"HTTP сессия для {self.platform_name} инициализирована")
    
    async def close_session(self) -> None:
        """Закрытие HTTP сессии"""
        if self.session:
            await self.session.close()
            self.logger.info(f"HTTP сессия для {self.platform_name} закрыта")
    
    async def fetch_page(self, url: str) -> Optional[str]:
        """
        Получение HTML страницы
        
        Args:
            url: URL страницы
            
        Returns:
            HTML контент или None при ошибке
        """
        try:
            if not self.session:
                await self.init_session()
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 403:
                    self.logger.warning(f"Доступ запрещен (403) для {url}")
                    return None
                elif response.status == 429:
                    self.logger.warning(f"Превышен лимит запросов (429) для {url}")
                    return None
                else:
                    self.logger.error(f"Ошибка {response.status} при запросе {url}")
                    return None
        except aiohttp.ClientError as e:
            self.logger.error(f"Ошибка сети при запросе {url}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Неожиданная ошибка при запросе {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """
        Парсинг HTML
        
        Args:
            html: HTML контент
            
        Returns:
            BeautifulSoup объект или None
        """
        try:
            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            self.logger.error(f"Ошибка парсинга HTML: {e}")
            return None
    
    def check_access(self, html: str) -> bool:
        """
        Проверка доступности контента (нет логина/капчи/2FA)
        
        Args:
            html: HTML контент
            
        Returns:
            True если контент доступен
        """
        if not html:
            return False
        
        # Проверяем признаки блокировки
        blocked_indicators = [
            'login', 'sign in', 'captcha', 'verification',
            '登录', '验证', 'blocked', 'access denied'
        ]
        
        html_lower = html.lower()
        for indicator in blocked_indicators:
            if indicator in html_lower:
                self.logger.warning(f"Обнаружен индикатор блокировки: {indicator}")
                return False
        
        return True
    
    @abstractmethod
    async def search_products(
        self, 
        keywords: List[str], 
        limit: int = 30
    ) -> List[Product]:
        """
        Поиск продуктов по ключевым словам
        
        Args:
            keywords: Список ключевых слов для поиска
            limit: Максимальное количество продуктов
            
        Returns:
            Список найденных продуктов
        """
        raise NotImplementedError
    
    @abstractmethod
    async def parse_product_details(
        self, 
        product_url: str
    ) -> Optional[Product]:
        """
        Парсинг деталей продукта
        
        Args:
            product_url: URL продукта
            
        Returns:
            Объект Product или None
        """
        raise NotImplementedError
    
    @abstractmethod
    async def get_trending_hashtags(self) -> List[str]:
        """
        Получение трендовых хэштегов
        
        Returns:
            Список хэштегов
        """
        raise NotImplementedError
    
    def extract_metrics(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлечение метрик из данных
        
        Args:
            data: Словарь с данными
            
        Returns:
            Словарь с метриками
        """
        metrics = {}
        
        # Пытаемся извлечь стандартные метрики
        view_keys = ['views', 'view_count', 'playCount', '播放量']
        like_keys = ['likes', 'like_count', 'diggCount', '点赞']
        comment_keys = ['comments', 'comment_count', 'commentCount', '评论']
        share_keys = ['shares', 'share_count', 'shareCount', '分享']
        
        for key in view_keys:
            if key in data and data[key]:
                metrics['views'] = data[key]
                break
        
        for key in like_keys:
            if key in data and data[key]:
                metrics['likes'] = data[key]
                break
        
        for key in comment_keys:
            if key in data and data[key]:
                metrics['comments'] = data[key]
                break
        
        for key in share_keys:
            if key in data and data[key]:
                metrics['shares'] = data[key]
                break
        
        return metrics

