"""
Запуск парсера в отдельном процессе
"""

import subprocess
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
import sys

from . import config as project_config
from . import logger

log = logger.get_logger("ParserRunner")

# Файл с настройками для парсера
SETTINGS_FILE = Path("config/bot_settings.json")

def load_settings() -> Dict[str, Any]:
    """Загрузить настройки из JSON"""
    default_settings = {
        "min_products": 3,
        "max_products_to_check": 4,
        "products_per_page": 20,
        "min_impressions": project_config.MIN_IMPRESSIONS,
        "days_back": project_config.DAYS_BACK,
        "headless": project_config.BROWSER_HEADLESS,
    }
    
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                user_settings = json.load(f)
                default_settings.update(user_settings)
        except Exception as e:
            log.warning(f"Ошибка при загрузке настроек: {e}")
    
    return default_settings

def save_settings(settings: Dict[str, Any]):
    """Сохранить настройки в JSON"""
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

def get_parser_command(settings: Dict[str, Any]) -> tuple:
    """Получить команду для запуска парсера с настройками"""
    import os
    import sys
    
    # Определяем правильный Python (тот же, что запустил бота)
    python_exe = sys.executable
    log.info(f"Используется Python: {python_exe}")
    
    # Устанавливаем переменные окружения
    env = os.environ.copy()
    env["MIN_PRODUCTS"] = str(settings['min_products'])
    env["MAX_PRODUCTS_TO_CHECK"] = str(settings['max_products_to_check'])
    env["PRODUCTS_PER_PAGE"] = str(settings['products_per_page'])
    env["MIN_IMPRESSIONS"] = str(settings['min_impressions'])
    env["DAYS_BACK"] = str(settings['days_back'])
    env["BROWSER_HEADLESS"] = str(settings['headless']).lower()
    
    # Используем тот же Python, что запустил бота
    return [python_exe, "test_parser_engine.py"], env

class ParserRunner:
    """Класс для управления запуском парсера"""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.start_time: Optional[datetime] = None
        self.settings: Dict[str, Any] = {}
    
    def is_running(self) -> bool:
        """Проверить, запущен ли парсер"""
        if not self.process:
            return False
        return self.process.poll() is None
    
    def start(self) -> bool:
        """Запустить парсер"""
        # Очищаем старый процесс, если он завершен
        if self.process and not self.is_running():
            log.debug("Очистка завершенного процесса")
            self.process = None
            self.start_time = None
        
        if self.is_running():
            log.warning("Парсер уже запущен")
            return False
        
        # Загружаем настройки
        self.settings = load_settings()
        
        # Получаем команду и переменные окружения
        cmd, env = get_parser_command(self.settings)
        
        try:
            log.info(f"Запуск команды: {' '.join(cmd)}")
            log.info(f"Рабочая директория: {Path.cwd()}")
            log.info(f"Настройки: min_products={self.settings.get('min_products')}, "
                    f"min_impressions={self.settings.get('min_impressions')}, "
                    f"days_back={self.settings.get('days_back')}")
            
            # Просто запускаем test_parser_engine.py
            # Запускаем без PIPE, чтобы логи шли в терминал в реальном времени
            # Это поможет видеть, что происходит с парсером
            self.process = subprocess.Popen(
                cmd,
                stdout=None,  # Вывод в терминал
                stderr=None,  # Ошибки в терминал
                env=env,
                cwd=Path.cwd()
            )
            
            self.start_time = datetime.now()
            log.info(f"✅ Парсер запущен: {' '.join(cmd)} (PID: {self.process.pid})")
            
            # Проверяем, что процесс действительно запустился
            import time
            time.sleep(0.5)  # Небольшая задержка для проверки
            if self.process.poll() is not None:
                # Процесс уже завершился
                return_code = self.process.returncode
                log.error(f"❌ Процесс завершился сразу после запуска! return_code={return_code}")
                log.error(f"   → Проверьте логи в терминале, где запущен бот")
                return False
            
            return True
            
        except FileNotFoundError as e:
            log.error(f"❌ Файл не найден: {e}")
            log.error(f"   Команда: {' '.join(cmd)}")
            log.error(f"   Рабочая директория: {Path.cwd()}")
            return False
        except Exception as e:
            log.error(f"❌ Ошибка при запуске парсера: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def stop(self) -> bool:
        """Остановить парсер"""
        if not self.is_running():
            return False
        
        try:
            self.process.terminate()
            # Ждем 5 секунд, затем убиваем принудительно
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            
            log.info("Парсер остановлен")
            return True
        except Exception as e:
            log.error(f"Ошибка при остановке парсера: {e}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Получить статус парсера"""
        # Если процесс завершен, очищаем его
        if self.process and not self.is_running():
            return_code = self.process.returncode
            log.info(f"📊 Процесс завершен, return_code={return_code}")
            
            # Пытаемся прочитать последние строки вывода
            # Примечание: если процесс уже завершен, stderr может быть уже прочитан
            # Основная диагностика происходит в start() при немедленном завершении
            
            self.process = None
            self.start_time = None
            return {
                "running": False,
                "start_time": None,
                "duration": None,
                "return_code": return_code,
            }
        
        if not self.process:
            return {
                "running": False,
                "start_time": None,
                "duration": None,
                "return_code": None,
            }
        
        running = self.is_running()
        duration = None
        
        if self.start_time:
            if running:
                duration = (datetime.now() - self.start_time).total_seconds()
            else:
                # Процесс завершен, но мы не знаем точное время завершения
                duration = "завершен"
        
        return_code = None
        if not running and self.process:
            return_code = self.process.returncode
        
        return {
            "running": running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "duration": duration,
            "return_code": return_code,
            "pid": self.process.pid if self.process else None,
        }

