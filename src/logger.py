"""
Логирование - настройка и управление логами
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import LOGS_DIR


def setup_logger(
    name: str = "ProductRadar",
    log_level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = True
) -> logging.Logger:
    """
    Настройка логгера
    
    Args:
        name: Имя логгера
        log_level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Логировать в файл
        log_to_console: Логировать в консоль
    
    Returns:
        Настроенный логгер
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    
    # Очищаем существующие обработчики
    logger.handlers.clear()
    
    # Формат логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Логирование в консоль
    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # Логирование в файл
    if log_to_file:
        # Создаем файл лога с датой
        log_file = LOGS_DIR / f"productradar_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)  # В файл пишем все уровни
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Глобальный логгер по умолчанию
_default_logger: Optional[logging.Logger] = None


def get_logger(name: str = "ProductRadar") -> logging.Logger:
    """
    Получить логгер (создает при первом вызове)
    
    Args:
        name: Имя логгера
    
    Returns:
        Логгер
    """
    global _default_logger
    if _default_logger is None:
        _default_logger = setup_logger(name)
    return _default_logger




