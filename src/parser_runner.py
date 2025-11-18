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
        "max_products_to_check": 15,
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
    
    def start(self, min_products: int = None) -> bool:
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
        
        # Переопределяем количество товаров, если указано
        if min_products is not None:
            self.settings["min_products"] = min_products
        
        # Получаем команду и переменные окружения
        cmd, env = get_parser_command(self.settings)
        
        try:
            log.info(f"Запуск команды: {' '.join(cmd)}")
            log.info(f"Рабочая директория: {Path.cwd()}")
            log.info(f"Настройки: min_products={self.settings.get('min_products')}, "
                    f"min_impressions={self.settings.get('min_impressions')}, "
                    f"days_back={self.settings.get('days_back')}")
            
            # Просто запускаем test_parser_engine.py
            # Читаем в байтах, чтобы избежать проблем с кодировкой
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # Читаем в байтах
                env=env,
                cwd=Path.cwd()
            )
            
            self.start_time = datetime.now()
            log.info(f"✅ Парсер запущен: {' '.join(cmd)} (PID: {self.process.pid})")
            
            # Проверяем, что процесс действительно запустился (синхронно, без await)
            import time
            time.sleep(0.5)  # Небольшая задержка для проверки
            if self.process.poll() is not None:
                # Процесс уже завершился
                return_code = self.process.returncode
                log.error(f"❌ Процесс завершился сразу после запуска! return_code={return_code}")
                
                # Пытаемся прочитать вывод
                try:
                    import sys
                    import io
                    
                    # Используем communicate() для чтения всего вывода
                    try:
                        # Читаем в байтах, затем декодируем с обработкой ошибок
                        stdout_bytes, stderr_bytes = self.process.communicate(timeout=2)
                        
                        # Декодируем с обработкой ошибок кодировки
                        def safe_decode(data):
                            if data is None:
                                return None
                            if isinstance(data, str):
                                return data
                            if not data:
                                return None
                            # Пробуем разные кодировки для Windows
                            for enc in ['utf-8', 'cp1251', 'cp866', 'latin1']:
                                try:
                                    decoded = data.decode(enc, errors='replace')
                                    # Проверяем, что декодирование прошло нормально
                                    if decoded:
                                        return decoded
                                except:
                                    continue
                            # Если ничего не помогло, используем utf-8 с заменой
                            return data.decode('utf-8', errors='replace')
                        
                        stderr = safe_decode(stderr_bytes) if stderr_bytes else None
                        stdout = safe_decode(stdout_bytes) if stdout_bytes else None
                        
                        if stderr:
                            # Разбиваем на строки и берем последние 30 строк
                            stderr_lines = stderr.split('\n')
                            if len(stderr_lines) > 30:
                                stderr_lines = stderr_lines[-30:]
                            stderr_text = "\n".join(stderr_lines)
                            log.error(f"   → stderr (последние 30 строк):\n{stderr_text}")
                        else:
                            log.warning(f"   → stderr пуст")
                        
                        if stdout:
                            # Берем последние 20 строк stdout
                            stdout_lines = stdout.split('\n')
                            if len(stdout_lines) > 20:
                                stdout_lines = stdout_lines[-20:]
                            stdout_text = "\n".join(stdout_lines)
                            log.info(f"   → stdout (последние 20 строк):\n{stdout_text[:1000]}")
                        else:
                            log.warning(f"   → stdout пуст")
                            
                    except subprocess.TimeoutExpired:
                        log.warning(f"   → Таймаут при чтении вывода процесса")
                        # Пытаемся убить процесс, если он еще жив
                        try:
                            self.process.kill()
                            self.process.communicate(timeout=1)
                        except:
                            pass
                    except Exception as e:
                        log.error(f"   → Ошибка при communicate(): {e}", exc_info=True)
                        
                except Exception as e:
                    log.error(f"   → Ошибка при чтении вывода процесса: {e}", exc_info=True)
                
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

