"""Утилиты для расчета метрик"""

from typing import Optional, List
import statistics
from datetime import datetime, timedelta

from src.models.product import Product
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


class MetricsCalculator:
    """Класс для расчета метрик продуктов"""
    
    @staticmethod
    def calculate_er(
        likes: Optional[int],
        comments: Optional[int],
        views: Optional[int]
    ) -> Optional[float]:
        """
        Расчет Engagement Rate
        ER = (likes + comments) / views * 100
        
        Args:
            likes: Количество лайков
            comments: Количество комментариев
            views: Количество просмотров
            
        Returns:
            ER в процентах или None
        """
        if not views or views == 0:
            return None
        
        total_engagement = 0
        
        if likes is not None:
            total_engagement += likes
        
        if comments is not None:
            total_engagement += comments
        elif likes is None and comments is not None:
            # Если лайки недоступны, используем приближение
            total_engagement = comments * 2
        
        er = (total_engagement / views) * 100
        return round(er, 2)
    
    @staticmethod
    def calculate_impulse_72h(
        views_72h: Optional[int],
        total_views: Optional[int],
        listing_age_days: Optional[int]
    ) -> float:
        """
        Расчет импульса за 72 часа
        
        Args:
            views_72h: Просмотры за 72 часа
            total_views: Всего просмотров
            listing_age_days: Возраст листинга в днях
            
        Returns:
            Оценка импульса 0-100
        """
        if not views_72h or not total_views or total_views == 0:
            return 0.0
        
        # Доля просмотров за последние 72ч
        recent_ratio = (views_72h / total_views) * 100
        
        # Бонус за свежесть
        if listing_age_days and listing_age_days > 0:
            # Молодые листинги получают бонус
            freshness_boost = max(0, (14 - listing_age_days) / 14) * 20
            recent_ratio += freshness_boost
        
        return min(100, recent_ratio)
    
    @staticmethod
    def estimate_ugc_share(
        video_count: int,
        branded_count: int
    ) -> float:
        """
        Оценка доли UGC (пользовательского контента)
        
        Args:
            video_count: Общее количество видео
            branded_count: Количество брендовых видео
            
        Returns:
            Доля UGC в процентах
        """
        if video_count == 0:
            return 0.0
        
        ugc_count = video_count - branded_count
        ugc_share = (ugc_count / video_count) * 100
        
        return round(min(100, max(0, ugc_share)), 2)
    
    @staticmethod
    def calculate_recency_score(listing_age_days: Optional[int]) -> float:
        """
        Оценка свежести продукта
        
        Args:
            listing_age_days: Возраст листинга в днях
            
        Returns:
            Оценка свежести 0-100
        """
        if listing_age_days is None:
            return 50.0  # Средняя оценка если неизвестно
        
        if listing_age_days <= 3:
            return 100.0
        elif listing_age_days <= 7:
            return 90.0
        elif listing_age_days <= 14:
            return 75.0
        elif listing_age_days <= 30:
            return 50.0
        elif listing_age_days <= 60:
            return 25.0
        else:
            return 10.0
    
    @staticmethod
    def calculate_ease_composite(
        reproducibility: Optional[int],
        sampling_ease: Optional[int]
    ) -> float:
        """
        Комплексная оценка доступности
        
        Args:
            reproducibility: Воспроизводимость 0-10
            sampling_ease: Простота выборки 0-10
            
        Returns:
            Оценка 0-100
        """
        if reproducibility is None and sampling_ease is None:
            return 50.0
        
        repro = reproducibility if reproducibility is not None else 5
        sampling = sampling_ease if sampling_ease is not None else 5
        
        # Среднее, умноженное на 10 для масштаба 0-100
        composite = ((repro + sampling) / 2) * 10
        
        return round(composite, 2)
    
    @staticmethod
    def normalize_er(er: float, all_products: List[Product]) -> float:
        """
        Нормализация ER относительно других продуктов (z-score)
        
        Args:
            er: ER продукта
            all_products: Список всех продуктов для сравнения
            
        Returns:
            Нормализованный ER 0-100
        """
        ers = [p.er_percent for p in all_products if p.er_percent is not None]
        
        if len(ers) < 2:
            return 50.0  # Если недостаточно данных
        
        mean_er = statistics.mean(ers)
        stdev_er = statistics.stdev(ers) if len(ers) > 1 else 1
        
        if stdev_er == 0:
            return 50.0
        
        # Z-score
        z = (er - mean_er) / stdev_er
        
        # Преобразуем z-score в шкалу 0-100
        # z от -3 до +3 обычно покрывает большинство значений
        normalized = ((z + 3) / 6) * 100
        
        return round(min(100, max(0, normalized)), 2)
    
    @staticmethod
    def calculate_trend_score(
        product: Product,
        all_products: List[Product],
        douyin_boost: bool = False
    ) -> float:
        """
        Расчет полного trendScore
        
        Args:
            product: Продукт
            all_products: Все продукты для нормализации
            douyin_boost: Использовать усиленные веса для Douyin
            
        Returns:
            trendScore 0-100
        """
        # Расчет компонентов
        impulse_72h = MetricsCalculator.calculate_impulse_72h(
            product.views_72h,
            product.total_views,
            product.listing_age_days
        )
        
        ugc_share = product.ugc_percent or 50.0
        
        er_z = MetricsCalculator.normalize_er(
            product.er_percent or 0,
            all_products
        ) if product.er_percent else 50.0
        
        recency_score = MetricsCalculator.calculate_recency_score(
            product.listing_age_days
        )
        
        ease_composite = MetricsCalculator.calculate_ease_composite(
            product.reproducibility_score,
            product.sampling_ease_score
        )
        
        # Расчет финального скора
        trend_score = product.calculate_trend_score(
            impulse_72h=impulse_72h,
            ugc_share=ugc_share,
            er_z=er_z,
            recency_score=recency_score,
            ease_composite=ease_composite,
            douyin_boost=douyin_boost
        )
        
        return trend_score

