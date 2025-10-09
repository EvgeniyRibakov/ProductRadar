"""Модели данных для продуктов"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl, field_validator


class Product(BaseModel):
    """Модель вирусного косметического продукта"""
    
    # Основная информация
    detection_date: str = Field(description="Дата обнаружения в формате YYYY-MM-DD")
    platform: str = Field(description="Платформа источника")
    category: str = Field(description="Категория: лицо/тело/волосы/декор")
    
    # Информация о продукте
    product_name_original: str = Field(description="Оригинальное название товара")
    product_name_translated: str = Field(description="Название товара на русском")
    sku_id: Optional[str] = Field(default=None, description="Артикул/SKU/ID/модель")
    
    # Ссылки
    product_url: Optional[str] = Field(default=None, description="Ссылка на товар")
    seller_url: Optional[str] = Field(default=None, description="Ссылка на продавца")
    video_urls: List[str] = Field(default_factory=list, description="Список ссылок на лучшие ролики")
    proof_screenshot_url: Optional[str] = Field(default=None, description="Скриншот/доказательство")
    
    # Цена и метрики
    price: Optional[str] = Field(default=None, description="Цена с валютой")
    total_views: Optional[int] = Field(default=None, description="Всего просмотров")
    views_24h: Optional[int] = Field(default=None, description="Просмотров за 24 часа")
    views_72h: Optional[int] = Field(default=None, description="Просмотров за 72 часа")
    comments_24h: Optional[int] = Field(default=None, description="Комментариев за 24 часа")
    
    # Показатели вовлеченности
    er_percent: Optional[float] = Field(default=None, description="ER в процентах")
    ugc_percent: Optional[float] = Field(default=None, description="Доля пользовательского контента в процентах")
    listing_age_days: Optional[int] = Field(default=None, description="Возраст листинга в днях")
    
    # Контент
    hashtag_peaks: Optional[str] = Field(default=None, description="Коротко о пиках по хэштегам")
    top_hooks_original: Optional[str] = Field(default=None, description="Топ-хуки (оригинал), 2 через /")
    top_hooks_translated: Optional[str] = Field(default=None, description="Топ-хуки (перевод), 2 через /")
    top_offers_original: Optional[str] = Field(default=None, description="Топ-офферы (оригинал)")
    top_offers_translated: Optional[str] = Field(default=None, description="Топ-офферы (перевод)")
    
    # Анализ
    why_works_original: Optional[str] = Field(default=None, description="Почему это работает (оригинал)")
    why_works_translated: Optional[str] = Field(default=None, description="Почему это работает (перевод)")
    insight: Optional[str] = Field(default=None, description="Insight - фича продукта (8-15 слов)")
    
    # Риски и оценки
    risks: Optional[str] = Field(default=None, description="Риски (претензии/IP)")
    reproducibility_score: Optional[int] = Field(default=None, ge=0, le=10, description="Воспроизводимость 0-10")
    sampling_ease_score: Optional[int] = Field(default=None, ge=0, le=10, description="Простота выборки 0-10")
    
    # Скоринг
    trend_score: Optional[float] = Field(default=None, ge=0, le=100, description="trendScore 0-100")
    priority: str = Field(default="B", description="Приоритет: A/B/C")
    status: str = Field(default="новый", description="Статус")
    responsible: Optional[str] = Field(default=None, description="Ответственный")
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Валидация категории"""
        allowed = ['лицо', 'тело', 'волосы', 'декор', 'кожа', 'макияж']
        if v.lower() not in allowed:
            raise ValueError(f"Категория должна быть одной из: {', '.join(allowed)}")
        return v.lower()
    
    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Валидация платформы"""
        allowed = [
            'TikTok Shop (США)', 'TikTok Shop (ЕС)', 'TikTok Shop (АСЕАН)',
            'RED', 'Taobao', 'Tmall', 'Olive Young', 'Amazon', 'Douyin',
            'TikTok', 'YouTube', 'Instagram', 'Xiaohongshu'
        ]
        if v not in allowed:
            raise ValueError(f"Платформа должна быть одной из: {', '.join(allowed)}")
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        """Валидация приоритета"""
        if v.upper() not in ['A', 'B', 'C']:
            raise ValueError("Приоритет должен быть A, B или C")
        return v.upper()
    
    def calculate_er(self, likes: Optional[int] = None, comments: Optional[int] = None, 
                     views: Optional[int] = None) -> Optional[float]:
        """
        Расчет ER (Engagement Rate)
        ER = (likes + comments) / views * 100
        """
        if views and views > 0:
            total_engagement = 0
            if likes:
                total_engagement += likes
            if comments:
                total_engagement += comments
            elif not likes and comments:
                # Если лайки недоступны, используем приближение
                total_engagement = comments * 2
            
            self.er_percent = round((total_engagement / views) * 100, 2)
            return self.er_percent
        return None
    
    def calculate_trend_score(self, impulse_72h: float, ugc_share: float, 
                             er_z: float, recency_score: float, 
                             ease_composite: float, 
                             douyin_boost: bool = False) -> float:
        """
        Расчет trendScore
        
        Для Douyin:
        trendScore = 0.45*Impulse72h + 0.30*UGCshare + 0.10*ERz + 0.10*RecencyScore + 0.05*EaseComposite
        
        Для остальных:
        trendScore = 0.35*Impulse72h + 0.25*UGCshare + 0.15*ERz + 0.15*RecencyScore + 0.10*EaseComposite
        """
        if douyin_boost:
            score = (
                0.45 * impulse_72h +
                0.30 * ugc_share +
                0.10 * er_z +
                0.10 * recency_score +
                0.05 * ease_composite
            )
        else:
            score = (
                0.35 * impulse_72h +
                0.25 * ugc_share +
                0.15 * er_z +
                0.15 * recency_score +
                0.10 * ease_composite
            )
        
        self.trend_score = round(min(100, max(0, score)), 2)
        
        # Автоматическое определение приоритета
        if self.trend_score >= 75:
            self.priority = 'A'
        elif self.trend_score < 45:
            self.priority = 'C'
        else:
            self.priority = 'B'
        
        return self.trend_score
    
    def to_csv_row(self) -> dict:
        """Конвертация в строку CSV согласно спецификации"""
        return {
            'Дата обнаружения': self.detection_date,
            'Платформа': self.platform,
            'Категория': self.category,
            'Название товара': self.product_name_original,
            'Ссылка на товар': self.product_url or '',
            'Ссылка на продавца': self.seller_url or '',
            'Цена': self.price or '',
            'Всего просмотров': self.total_views or '',
            'просмотров за 24 часа': self.views_24h or '',
            'комментариев за 24 часа': self.comments_24h or '',
            'ER, %': self.er_percent or '',
            'Доля пользовательского контента, %': self.ugc_percent or '',
            'Возраст листинга, дни': self.listing_age_days or '',
            'Коротко о пиках по хэштегам': self.hashtag_peaks or '',
            'Топ-хуки': self.top_hooks_translated or '',
            'Топ-офферы': self.top_offers_translated or '',
            'Почему это работает': self.why_works_translated or '',
            'Риски (претензии/интеллектуальная собственность)': self.risks or '',
            'Воспроизводимость, 0–10': self.reproducibility_score or '',
            'Простота выборки, 0–10': self.sampling_ease_score or '',
            'trendScore, 0–100': self.trend_score or '',
            'Приоритет': self.priority,
            'Статус': self.status,
            'Ответственный': self.responsible or '',
            'Скрин/доказательство (URL)': self.proof_screenshot_url or ''
        }


class ProductCollection(BaseModel):
    """Коллекция продуктов"""
    
    products: List[Product] = Field(default_factory=list)
    total_count: int = Field(default=0)
    
    def add_product(self, product: Product) -> None:
        """Добавить продукт в коллекцию"""
        self.products.append(product)
        self.total_count = len(self.products)
    
    def deduplicate(self) -> int:
        """
        Удалить дубликаты по бренду+SKU или URL
        Возвращает количество удаленных дубликатов
        """
        seen = set()
        unique_products = []
        duplicates_count = 0
        
        for product in self.products:
            # Создаем ключ для дедупликации
            key = None
            if product.sku_id:
                key = f"{product.product_name_original}_{product.sku_id}"
            elif product.product_url:
                key = product.product_url
            else:
                key = f"{product.product_name_original}_{product.platform}"
            
            if key not in seen:
                seen.add(key)
                unique_products.append(product)
            else:
                duplicates_count += 1
        
        self.products = unique_products
        self.total_count = len(self.products)
        return duplicates_count
    
    def filter_by_platform(self, platform: str) -> 'ProductCollection':
        """Фильтрация по платформе"""
        filtered = ProductCollection()
        for product in self.products:
            if product.platform == platform:
                filtered.add_product(product)
        return filtered
    
    def sort_by_trend_score(self, descending: bool = True) -> None:
        """Сортировка по trendScore"""
        self.products.sort(
            key=lambda p: p.trend_score or 0,
            reverse=descending
        )

