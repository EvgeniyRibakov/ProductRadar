"""Script to run the ProductRadar agent"""

import asyncio
import sys
import os
from pathlib import Path
import argparse

# Добавляем корневую директорию в путь
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.agents.product_radar_agent import ProductRadarAgent
from src.config.settings import settings
from src.utils.logger import setup_logger


logger = setup_logger(__name__, log_file="logs/agent.log")


async def main():
    """Главная функция для запуска агента"""
    parser = argparse.ArgumentParser(description='ProductRadar - Поиск вирусных косметических товаров')
    parser.add_argument('--min-products', type=int, default=30, help='Минимальное количество продуктов')
    parser.add_argument('--target-products', type=int, default=50, help='Целевое количество продуктов')
    parser.add_argument('--douyin-target', type=int, default=25, help='Целевое количество с Douyin')
    parser.add_argument('--no-douyin-priority', action='store_true', help='Отключить приоритет Douyin')
    parser.add_argument('--google-creds', type=str, default=None, help='Путь к Google credentials')
    
    args = parser.parse_args()
    
    logger.info("="*70)
    logger.info("ЗАПУСК PRODUCTRADAR AI AGENT")
    logger.info("="*70)
    logger.info(f"Минимум продуктов: {args.min_products}")
    logger.info(f"Целевое количество: {args.target_products}")
    logger.info(f"Douyin target: {args.douyin_target}")
    logger.info(f"Douyin приоритет: {not args.no_douyin_priority}")
    logger.info(f"AI модель: {settings.agent_model}")
    logger.info("="*70)
    
    # Конфигурация агента
    config = {
        'min_products': args.min_products,
        'target_products': args.target_products,
        'douyin_target': args.douyin_target,
        'douyin_priority': not args.no_douyin_priority,
        'google_credentials_path': args.google_creds
    }
    
    try:
        # Создаем и запускаем агента
        agent = ProductRadarAgent(config=config)
        
        logger.info("Агент инициализирован, начинаем работу...")
        
        result = await agent.run()
        
        # Выводим результаты
        logger.info("\n" + "="*70)
        logger.info("РЕЗУЛЬТАТЫ РАБОТЫ АГЕНТА")
        logger.info("="*70)
        logger.info(f"Статус: {result['status']}")
        logger.info(f"Всего продуктов: {result.get('total_products', 0)}")
        logger.info(f"Продуктов с Douyin: {result.get('douyin_products', 0)}")
        
        if result.get('export'):
            export = result['export']
            logger.info(f"Локальный файл: {export.get('local_path', 'N/A')}")
            logger.info(f"Google Drive: {export.get('drive_url', 'N/A')}")
        
        logger.info("="*70)
        
        if result['status'] == 'success':
            logger.info("✓ Агент завершил работу успешно!")
            return 0
        else:
            logger.error(f"✗ Агент завершился с ошибкой: {result.get('error')}")
            return 1
            
    except KeyboardInterrupt:
        logger.warning("\n\nПрервано пользователем")
        return 130
    except Exception as e:
        logger.error(f"\n\nКритическая ошибка: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

