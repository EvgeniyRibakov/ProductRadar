"""Base Agent class"""

from typing import Any, Dict, Optional
from abc import ABC, abstractmethod


class BaseAgent(ABC):
    """Базовый класс для всех агентов"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация агента
        
        Args:
            config: Конфигурация агента
        """
        self.config = config or {}
        self.setup()
    
    def setup(self):
        """Настройка агента"""
        pass
    
    @abstractmethod
    async def run(self, task: str, **kwargs) -> Any:
        """
        Выполнить задачу
        
        Args:
            task: Описание задачи
            **kwargs: Дополнительные параметры
            
        Returns:
            Результат выполнения задачи
        """
        raise NotImplementedError
    
    @abstractmethod
    async def process(self, input_data: Any) -> Any:
        """
        Обработать входные данные
        
        Args:
            input_data: Входные данные
            
        Returns:
            Обработанные данные
        """
        raise NotImplementedError

