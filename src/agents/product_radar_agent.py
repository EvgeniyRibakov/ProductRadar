"""Главный агент для поиска вирусных продуктов"""

from typing import List, Optional, Dict
from datetime import datetime
import asyncio

from src.agents.base_agent import BaseAgent
from src.models.product import Product, ProductCollection
from src.parsers.douyin_parser import DouyinParser
from src.parsers.tiktok_parser import TikTokParser
from src.parsers.xiaohongshu_parser import XiaohongshuParser
from src.utils.translator import Translator
from src.utils.metrics import MetricsCalculator
from src.utils.exporter import ProductExporter
from src.utils.logger import setup_logger


class ProductRadarAgent(BaseAgent):
    """Агент для поиска вирусных косметических продуктов"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Инициализация агента
        
        Args:
            config: Конфигурация агента
        """
        super().__init__(config)
        self.logger = setup_logger(__name__)
        
        # Инициализация компонентов
        self.translator = Translator(use_openai=True)
        self.metrics_calculator = MetricsCalculator()
        self.exporter = ProductExporter(
            google_credentials_path=config.get('google_credentials_path') if config else None
        )
        
        # Парсеры платформ
        self.parsers = {
            'douyin': DouyinParser(),
            'tiktok_us': TikTokParser(region='US'),
            'tiktok_eu': TikTokParser(region='EU'),
            'xiaohongshu': XiaohongshuParser()
        }
        
        # Коллекция продуктов
        self.products = ProductCollection()
        
        # Целевые параметры
        self.min_products = config.get('min_products', 30) if config else 30
        self.target_products = config.get('target_products', 50) if config else 50
        self.douyin_priority = config.get('douyin_priority', True) if config else True
        self.douyin_target = config.get('douyin_target', 25) if config else 25
    
    def setup(self):
        """Настройка агента"""
        self.logger.info("ProductRadar Agent инициализирован")
        self.logger.info(f"Цель: {self.min_products}-{self.target_products} продуктов")
        self.logger.info(f"Douyin приоритет: {self.douyin_priority} ({self.douyin_target} продуктов)")
    
    async def run(self, task: str = None, **kwargs) -> Dict:
        """
        Выполнить основную задачу агента
        
        Args:
            task: Описание задачи
            **kwargs: Дополнительные параметры
            
        Returns:
            Результат выполнения
        """
        self.logger.info("="*60)
        self.logger.info("Запуск ProductRadar Agent")
        self.logger.info("="*60)
        
        try:
            # Шаг 1: Сбор продуктов с платформ
            await self.collect_products()
            
            # Шаг 2: Обработка и обогащение данных
            await self.process_products()
            
            # Шаг 3: Дедупликация
            self.deduplicate_products()
            
            # Шаг 4: Расчет метрик и скоринг
            self.calculate_scores()
            
            # Шаг 5: Фильтрация и сортировка
            self.finalize_selection()
            
            # Шаг 6: Экспорт результатов
            export_result = await self.export_results()
            
            # Формирование итогового отчета
            result = {
                'status': 'success',
                'total_products': self.products.total_count,
                'douyin_products': len(self.products.filter_by_platform('Douyin').products),
                'export': export_result,
                'timestamp': datetime.now().isoformat()
            }
            
            self.logger.info("="*60)
            self.logger.info(f"ProductRadar Agent завершен успешно: {result['total_products']} продуктов")
            self.logger.info("="*60)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при выполнении агента: {e}", exc_info=True)
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def collect_products(self) -> None:
        """Сбор продуктов со всех платформ"""
        self.logger.info("\n--- ШАГ 1: Сбор продуктов ---")
        
        tasks = []
        
        # Douyin - приоритетная платформа
        if self.douyin_priority:
            self.logger.info(f"Приоритет Douyin: собираем {self.douyin_target} продуктов")
            tasks.append(self._collect_from_douyin(self.douyin_target))
        
        # Остальные платформы
        remaining_target = self.target_products - self.douyin_target
        per_platform = remaining_target // 3
        
        tasks.extend([
            self._collect_from_tiktok('us', per_platform),
            self._collect_from_tiktok('eu', per_platform),
            self._collect_from_xiaohongshu(per_platform)
        ])
        
        # Параллельный сбор
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обработка результатов
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Ошибка при сборе: {result}")
            elif isinstance(result, list):
                for product in result:
                    self.products.add_product(product)
        
        self.logger.info(f"Всего собрано продуктов: {self.products.total_count}")
    
    async def _collect_from_douyin(self, limit: int) -> List[Product]:
        """Сбор продуктов с Douyin"""
        self.logger.info(f"Сбор с Douyin (лимит: {limit})")
        
        parser = self.parsers['douyin']
        
        # Получаем хэштеги для всех категорий
        keywords = []
        for category in ['волосы', 'лицо', 'тело', 'декор']:
            keywords.extend(parser.get_hashtags_by_category(category))
        
        async with parser:
            products = await parser.search_products(keywords, limit=limit)
        
        self.logger.info(f"Собрано с Douyin: {len(products)} продуктов")
        return products
    
    async def _collect_from_tiktok(self, region: str, limit: int) -> List[Product]:
        """Сбор продуктов с TikTok"""
        self.logger.info(f"Сбор с TikTok {region.upper()} (лимит: {limit})")
        
        parser_key = f'tiktok_{region}'
        parser = self.parsers[parser_key]
        
        keywords = await parser.get_trending_hashtags()
        
        async with parser:
            products = await parser.search_products(keywords[:10], limit=limit)
        
        self.logger.info(f"Собрано с TikTok {region.upper()}: {len(products)} продуктов")
        return products
    
    async def _collect_from_xiaohongshu(self, limit: int) -> List[Product]:
        """Сбор продуктов с Xiaohongshu"""
        self.logger.info(f"Сбор с Xiaohongshu (лимит: {limit})")
        
        parser = self.parsers['xiaohongshu']
        keywords = await parser.get_trending_hashtags()
        
        async with parser:
            products = await parser.search_products(keywords[:10], limit=limit)
        
        self.logger.info(f"Собрано с Xiaohongshu: {len(products)} продуктов")
        return products
    
    async def process_products(self) -> None:
        """Обработка и обогащение данных продуктов"""
        self.logger.info("\n--- ШАГ 2: Обработка данных ---")
        
        for i, product in enumerate(self.products.products, 1):
            try:
                # Перевод полей
                if product.product_name_original and not product.product_name_translated:
                    product.product_name_translated = await self.translator.translate_chinese_to_russian(
                        product.product_name_original,
                        'название продукта'
                    )
                
                if product.top_hooks_original and not product.top_hooks_translated:
                    product.top_hooks_translated = await self.translator.translate_chinese_to_russian(
                        product.top_hooks_original,
                        'хук'
                    )
                
                if product.top_offers_original and not product.top_offers_translated:
                    product.top_offers_translated = await self.translator.translate_chinese_to_russian(
                        product.top_offers_original,
                        'оффер'
                    )
                
                if product.why_works_original and not product.why_works_translated:
                    product.why_works_translated = await self.translator.translate_chinese_to_russian(
                        product.why_works_original,
                        'описание'
                    )
                
                if i % 10 == 0:
                    self.logger.info(f"Обработано: {i}/{self.products.total_count}")
                    
            except Exception as e:
                self.logger.error(f"Ошибка при обработке продукта {i}: {e}")
        
        self.logger.info(f"Обработка завершена: {self.products.total_count} продуктов")
    
    def deduplicate_products(self) -> None:
        """Дедупликация продуктов"""
        self.logger.info("\n--- ШАГ 3: Дедупликация ---")
        
        initial_count = self.products.total_count
        duplicates_removed = self.products.deduplicate()
        
        self.logger.info(f"Удалено дубликатов: {duplicates_removed}")
        self.logger.info(f"Уникальных продуктов: {self.products.total_count}")
    
    def calculate_scores(self) -> None:
        """Расчет метрик и trendScore"""
        self.logger.info("\n--- ШАГ 4: Расчет метрик ---")
        
        for product in self.products.products:
            try:
                # Определяем, нужен ли Douyin boost
                douyin_boost = product.platform == 'Douyin'
                
                # Расчет trendScore
                self.metrics_calculator.calculate_trend_score(
                    product,
                    self.products.products,
                    douyin_boost=douyin_boost
                )
                
            except Exception as e:
                self.logger.error(f"Ошибка при расчете метрик для {product.product_name_original}: {e}")
        
        self.logger.info("Расчет метрик завершен")
    
    def finalize_selection(self) -> None:
        """Финализация выборки - фильтрация и сортировка"""
        self.logger.info("\n--- ШАГ 5: Финализация ---")
        
        # Сортировка по trendScore
        self.products.sort_by_trend_score(descending=True)
        
        # Ограничение до целевого количества
        if self.products.total_count > self.target_products:
            self.products.products = self.products.products[:self.target_products]
            self.products.total_count = len(self.products.products)
        
        # Статистика по приоритетам
        priority_stats = {
            'A': len([p for p in self.products.products if p.priority == 'A']),
            'B': len([p for p in self.products.products if p.priority == 'B']),
            'C': len([p for p in self.products.products if p.priority == 'C'])
        }
        
        self.logger.info(f"Финальная выборка: {self.products.total_count} продуктов")
        self.logger.info(f"Приоритеты: A={priority_stats['A']}, B={priority_stats['B']}, C={priority_stats['C']}")
    
    async def export_results(self) -> Dict:
        """Экспорт результатов"""
        self.logger.info("\n--- ШАГ 6: Экспорт результатов ---")
        
        result = self.exporter.export_and_upload(
            products=self.products.products,
            save_locally=True,
            upload_to_drive=True
        )
        
        self.logger.info(f"Локальный файл: {result.get('local_path')}")
        self.logger.info(f"Google Drive: {result.get('drive_url')}")
        
        return result
    
    async def process(self, input_data) -> Dict:
        """
        Обработка входных данных
        
        Args:
            input_data: Входные данные
            
        Returns:
            Результат обработки
        """
        return await self.run()

