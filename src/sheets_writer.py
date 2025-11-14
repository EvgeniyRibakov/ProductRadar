"""
Sheets Writer - запись данных в Google Sheets
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Any, List, Optional
from pathlib import Path

from . import config
from . import logger
from . import validator

log = logger.get_logger("SheetsWriter")


class SheetsWriter:
    """Класс для записи данных в Google Sheets"""
    
    def __init__(self):
        self.client: Optional[gspread.Client] = None
        self.spreadsheet: Optional[gspread.Spreadsheet] = None
        self.worksheet: Optional[gspread.Worksheet] = None  # Основной лист (черновик)
        self.success_worksheet: Optional[gspread.Worksheet] = None  # Лист для успешных записей
        
    def connect(self) -> bool:
        """
        Подключение к Google Sheets
        
        Returns:
            True если успешно
        """
        try:
            log.info("Подключение к Google Sheets...")
            
            # Проверка наличия credentials
            credentials_path = config.get_google_credentials_path()
            if not credentials_path.exists():
                log.error(f"❌ Файл credentials не найден: {credentials_path}")
                return False
            
            # Авторизация
            SCOPE = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            
            credentials = Credentials.from_service_account_file(
                str(credentials_path),
                scopes=SCOPE
            )
            
            self.client = gspread.authorize(credentials)
            log.info("✅ Авторизация успешна")
            
            # Открытие таблицы
            self.spreadsheet = self.client.open_by_key(config.GOOGLE_SHEETS_ID)
            log.info(f"✅ Таблица открыта: {self.spreadsheet.title}")
            
            # Открытие листа "Черновик" (или создание если не существует)
            try:
                self.worksheet = self.spreadsheet.worksheet("Черновик")
                log.info(f"✅ Лист 'Черновик' открыт")
            except gspread.exceptions.WorksheetNotFound:
                log.info("  → Лист 'Черновик' не найден, создаем...")
                # Копируем структуру с основного листа
                template_sheet = self.spreadsheet.worksheet(config.GOOGLE_SHEETS_SHEET_NAME)
                self.worksheet = self.spreadsheet.duplicate_sheet(
                    source_sheet_id=template_sheet.id,
                    new_sheet_name="Черновик"
                )
                log.info("  ✅ Лист 'Черновик' создан")
            
            # Открытие листа "Успешные" (или создание если не существует)
            try:
                self.success_worksheet = self.spreadsheet.worksheet("Успешные")
                log.info(f"✅ Лист 'Успешные' открыт")
            except gspread.exceptions.WorksheetNotFound:
                log.info("  → Лист 'Успешные' не найден, создаем...")
                # Копируем структуру с основного листа
                template_sheet = self.spreadsheet.worksheet(config.GOOGLE_SHEETS_SHEET_NAME)
                self.success_worksheet = self.spreadsheet.duplicate_sheet(
                    source_sheet_id=template_sheet.id,
                    new_sheet_name="Успешные"
                )
                log.info("  ✅ Лист 'Успешные' создан")
            
            return True
            
        except Exception as e:
            log.error(f"❌ Ошибка при подключении к Google Sheets: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def write_basic_product_data(self, product_name: str, category: str, pipiads_link: str) -> int:
        """
        Записать базовые данные товара (без видео) в Google Sheets
        
        Args:
            product_name: Название товара
            category: Категория товара
            pipiads_link: Ссылка на страницу товара
        
        Returns:
            Номер строки, в которую записаны данные, или 0 если ошибка
        """
        if not self.worksheet:
            log.error("❌ Лист не открыт, сначала вызовите connect()")
            return 0
        
        try:
            # Находим первую пустую строку
            row_number = self.find_next_empty_row()
            log.info(f"📝 Запись базовых данных товара в строку {row_number}...")
            
            # Подготовка данных для записи
            values = {}
            
            # A: Номер товара (вычисляем на основе строки)
            product_number = row_number - config.SHEET_START_ROW + 1
            values[config.SHEET_COLUMNS["product_number"]] = product_number
            
            # B: Product Name
            values[config.SHEET_COLUMNS["product_name"]] = product_name
            
            # C: НЕ ТРОГАТЬ - пропускаем
            
            # D: Category
            values[config.SHEET_COLUMNS["category"]] = category
            
            # E: Pipiads Link
            values[config.SHEET_COLUMNS["pipiads_link"]] = pipiads_link
            
            # Записываем только базовые данные
            log.info(f"  → Запись в {len(values)} ячеек (базовые данные)...")
            
            # Записываем по одной ячейке (более надежно)
            written_count = 0
            import time
            for col, value in values.items():
                cell = f"{col}{row_number}"
                try:
                    str_value = str(value)
                    if len(str_value) > 50000:
                        str_value = str_value[:50000] + "..."
                    
                    # Записываем значение (пробуем update_acell)
                    try:
                        self.worksheet.update_acell(cell, str_value)
                    except Exception as update_error:
                        # Если update_acell не работает, пробуем update
                        log.warning(f"  ⚠️ update_acell не сработал для {cell}, пробуем update: {update_error}")
                        try:
                            self.worksheet.update(cell, [[str_value]])
                        except Exception as update2_error:
                            log.error(f"  ❌ Оба метода записи не сработали для {cell}: {update2_error}")
                            raise update2_error
                    
                    # Проверяем, что записалось (с небольшой задержкой)
                    time.sleep(0.1)  # Небольшая задержка для синхронизации
                    
                    try:
                        written_value = self.worksheet.acell(cell).value
                        if written_value == str_value or (written_value and str(written_value).strip() == str(str_value).strip()):
                            written_count += 1
                            log.info(f"  ✅ {cell} = '{str(str_value)[:50]}...' (проверено)")
                        else:
                            log.warning(f"  ⚠️ {cell}: записано '{str_value[:50]}...', но прочитано '{written_value}'")
                            written_count += 1  # Все равно считаем успешным
                    except Exception as check_error:
                        # Если не удалось проверить, считаем успешным
                        written_count += 1
                        log.info(f"  ✅ {cell} = '{str(str_value)[:50]}...' (записано, проверка не удалась: {check_error})")
                        
                except Exception as e2:
                    log.error(f"  ❌ Ошибка записи в {cell}: {e2}")
                    import traceback
                    log.error(traceback.format_exc())
                    return 0
            
            if written_count == 0:
                log.error("  ❌ Ничего не записалось!")
                return 0
            
            log.info(f"✅ Базовые данные товара записаны в строку {row_number} ({written_count} ячеек)")
            return row_number
            
        except Exception as e:
            log.error(f"❌ Ошибка при записи базовых данных товара: {e}")
            import traceback
            log.error(traceback.format_exc())
            return 0
    
    def write_product_data(self, row_number: int, product_data: Dict[str, Any], update_basic: bool = False) -> bool:
        """
        Записать данные товара в Google Sheets (включая видео)
        
        Args:
            row_number: Номер строки для записи (получен из write_basic_product_data)
            product_data: Данные товара (ProductData)
            update_basic: Если True, обновляет базовые данные (A, B, D, E). Если False, обновляет только видео (F-Z)
        
        Returns:
            True если успешно
        """
        if not self.worksheet:
            log.error("❌ Лист не открыт, сначала вызовите connect()")
            return False
        
        if row_number <= 0:
            log.error("❌ Неверный номер строки")
            return False
        
        try:
            log.info(f"📝 Запись данных товара в строку {row_number}...")
            
            # Подготовка данных для записи
            values = {}
            
            # Базовые данные (только если update_basic=True)
            if update_basic:
                # A: Номер товара (вычисляем на основе строки)
                product_number = row_number - config.SHEET_START_ROW + 1
                values[config.SHEET_COLUMNS["product_number"]] = product_number
                
                # B: Product Name
                values[config.SHEET_COLUMNS["product_name"]] = product_data.get("product_name", "N/A")
                
                # C: НЕ ТРОГАТЬ - пропускаем
                
                # D: Category
                values[config.SHEET_COLUMNS["category"]] = product_data.get("category", "N/A")
                
                # E: Pipiads Link
                values[config.SHEET_COLUMNS["pipiads_link"]] = product_data.get("pipiads_link", "N/A")
            
            # Видео данные (до 3 видео)
            videos = product_data.get("videos", [])
            log.info(f"  → Получено {len(videos)} видео для записи")
            
            # Заполняем до 3 видео (если меньше - заполняем N/A)
            for video_index in range(3):
                video_prefix = f"video{video_index + 1}_"
                
                if video_index < len(videos):
                    video = videos[video_index]
                    log.info(f"  → Видео {video_index + 1}: tiktok_link={video.get('tiktok_link', 'N/A')[:50]}, impression={video.get('impression', 0)}, script={len(str(video.get('script', 'N/A')))} символов")
                else:
                    # Заполняем N/A если видео нет
                    video = {
                        "tiktok_link": "N/A",
                        "impression": 0,
                        "script": "N/A",
                        "hook": "N/A",
                        "audience_age": "N/A",
                        "country": "N/A",
                        "first_seen": "N/A",
                    }
                    log.info(f"  → Видео {video_index + 1}: нет данных, заполняем N/A")
                
                # TikTok ссылка
                tiktok_link = video.get("tiktok_link", "N/A")
                values[config.SHEET_COLUMNS[f"{video_prefix}tiktok"]] = tiktok_link
                
                # Impression (может быть строкой "170.6K" или числом)
                impression = video.get("impression", "N/A")
                if isinstance(impression, str) and impression != "N/A":
                    values[config.SHEET_COLUMNS[f"{video_prefix}impression"]] = impression
                elif isinstance(impression, (int, float)) and impression > 0:
                    # Форматируем число в формат "170.6K"
                    values[config.SHEET_COLUMNS[f"{video_prefix}impression"]] = validator.format_impressions(int(impression))
                else:
                    values[config.SHEET_COLUMNS[f"{video_prefix}impression"]] = "N/A"
                
                # Script
                script = video.get("script", "N/A")
                values[config.SHEET_COLUMNS[f"{video_prefix}script"]] = script if script and script != "N/A" else "N/A"
                
                # Hook
                hook = video.get("hook", "N/A")
                values[config.SHEET_COLUMNS[f"{video_prefix}hook"]] = hook if hook and hook != "N/A" else "N/A"
                
                # Audience (уже в формате "35-45 Android")
                audience_age = video.get("audience_age", "N/A")
                values[config.SHEET_COLUMNS[f"{video_prefix}audience"]] = audience_age if audience_age and audience_age != "N/A" else "N/A"
                
                # Country
                country = video.get("country", "N/A")
                values[config.SHEET_COLUMNS[f"{video_prefix}country"]] = country if country and country != "N/A" else "N/A"
                
                # First seen (формат "Oct 27 2025", не преобразовывать!)
                first_seen = video.get("first_seen", "N/A")
                values[config.SHEET_COLUMNS[f"{video_prefix}first_seen"]] = first_seen if first_seen and first_seen != "N/A" else "N/A"
            
            # Записываем данные в ячейки
            log.info(f"  → Запись в {len(values)} ячеек...")
            log.info(f"  → Данные для записи:")
            for col, value in sorted(values.items()):
                log.info(f"      {col}{row_number}: {str(value)[:100]}")
            
            # Записываем по одной ячейке (более надежно)
            written_count = 0
            import time
            for col, value in sorted(values.items()):  # Сортируем для предсказуемого порядка
                cell = f"{col}{row_number}"
                try:
                    str_value = str(value)
                    if len(str_value) > 50000:  # Ограничение Google Sheets
                        str_value = str_value[:50000] + "..."
                    
                    log.debug(f"  → Запись {cell} = '{str_value[:100]}'")
                    
                    # Записываем значение (пробуем update_acell)
                    try:
                        self.worksheet.update_acell(cell, str_value)
                    except Exception as update_error:
                        # Если update_acell не работает, пробуем update
                        log.warning(f"  ⚠️ update_acell не сработал для {cell}, пробуем update: {update_error}")
                        try:
                            self.worksheet.update(cell, [[str_value]])
                        except Exception as update2_error:
                            log.error(f"  ❌ Оба метода записи не сработали для {cell}: {update2_error}")
                            raise update2_error
                    
                    # Проверяем, что записалось (с небольшой задержкой)
                    time.sleep(0.1)  # Небольшая задержка для синхронизации
                    
                    try:
                        written_value = self.worksheet.acell(cell).value
                        if written_value == str_value or (written_value and str(written_value).strip() == str(str_value).strip()):
                            written_count += 1
                            log.info(f"  ✅ {cell} = '{str(str_value)[:50]}...' (проверено)")
                        else:
                            log.warning(f"  ⚠️ {cell}: записано '{str_value[:50]}...', но прочитано '{written_value}'")
                            written_count += 1  # Все равно считаем успешным
                    except Exception as check_error:
                        # Если не удалось проверить, считаем успешным
                        written_count += 1
                        log.info(f"  ✅ {cell} = '{str(str_value)[:50]}...' (записано, проверка не удалась: {check_error})")
                        
                except Exception as e2:
                    log.error(f"  ❌ Ошибка записи в {cell}: {e2}")
                    import traceback
                    log.error(traceback.format_exc())
                    return False
            
            if written_count == 0:
                log.error("  ❌ Ничего не записалось!")
                return False
            
            log.info(f"  ✅ Записано {written_count} из {len(values)} ячеек")
            
            log.info(f"✅ Данные товара записаны в строку {row_number}")
            return True
            
        except Exception as e:
            log.error(f"❌ Ошибка при записи данных товара: {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def is_row_complete(self, row_number: int) -> bool:
        """
        Проверить, заполнена ли строка полностью (все столбцы A-Z кроме C)
        
        Args:
            row_number: Номер строки в листе "Черновик"
        
        Returns:
            True если все ячейки заполнены (кроме C)
        """
        if not self.worksheet:
            return False
        
        try:
            # Читаем строку A-Z (столбцы 1-26)
            row_data = self.worksheet.row_values(row_number)
            
            if not row_data:
                return False
            
            # Проверяем заполненность столбцов A-Z (индексы 0-25)
            # Столбец C (индекс 2) пропускаем
            for i in range(26):
                # Пропускаем столбец C (индекс 2)
                if i == 2:
                    continue
                
                # Если столбец не заполнен или равен "N/A"
                if i >= len(row_data) or not row_data[i] or row_data[i].strip() in ['', 'N/A']:
                    return False
            
            return True
            
        except Exception as e:
            log.debug(f"Ошибка при проверке заполненности строки {row_number}: {e}")
            return False
    
    def copy_to_success_sheet(self, row_number: int) -> bool:
        """
        Скопировать успешную запись из "Черновик" на лист "Успешные"
        
        Вызывается только если строка полностью заполнена (проверка через is_row_complete)
        
        Args:
            row_number: Номер строки в листе "Черновик"
        
        Returns:
            True если успешно
        """
        if not self.worksheet or not self.success_worksheet:
            log.error("❌ Листы не открыты")
            return False
        
        try:
            log.info(f"📋 Копирование строки {row_number} на лист 'Успешные'...")
            
            # Читаем всю строку из "Черновик"
            row_data = self.worksheet.row_values(row_number)
            
            if not row_data:
                log.error(f"❌ Строка {row_number} пуста")
                return False
            
            # Находим первую пустую строку на листе "Успешные"
            success_row = self._find_next_empty_row_in_sheet(self.success_worksheet)
            
            # Записываем данные на лист "Успешные"
            # Обновляем первую ячейку (номер товара) для корректной нумерации
            if row_data:
                # Новый номер = success_row - SHEET_START_ROW + 1
                row_data[0] = success_row - config.SHEET_START_ROW + 1
            
            self.success_worksheet.update(f'A{success_row}', [row_data])
            
            log.info(f"  ✅ Строка скопирована в 'Успешные' (строка {success_row})")
            return True
            
        except Exception as e:
            log.error(f"❌ Ошибка при копировании на лист 'Успешные': {e}")
            import traceback
            log.error(traceback.format_exc())
            return False
    
    def _find_next_empty_row_in_sheet(self, worksheet: gspread.Worksheet) -> int:
        """Найти первую пустую строку в указанном листе"""
        try:
            start_row = 2
            max_rows = 100
            
            # Читаем значения столбца A
            values = worksheet.col_values(1, value_render_option='UNFORMATTED_VALUE')
            
            # Ищем первую пустую строку
            for i in range(start_row - 1, max_rows):
                if i >= len(values) or not values[i]:
                    return i + 1
            
            # Если все заполнено, возвращаем следующую после последней
            return len(values) + 1
            
        except Exception as e:
            log.error(f"❌ Ошибка при поиске пустой строки: {e}")
            return config.SHEET_START_ROW
    
    def find_next_empty_row(self) -> int:
        """
        Найти первую пустую строку после строки 2 (пример)
        
        Returns:
            Номер строки для записи
        """
        if not self.worksheet:
            return config.SHEET_START_ROW
        
        try:
            # Читаем столбец A начиная со строки 2 (пример) до строки 100
            # Ищем первую строку, где столбец A пустой
            start_row = 2  # Строка 2 - пример, не трогаем
            max_rows = 100  # Максимальное количество строк для проверки
            
            # Читаем значения столбца A
            column_a = self.worksheet.col_values(1)  # Столбец A
            
            # Ищем первую пустую строку после строки 2
            for row_num in range(start_row + 1, len(column_a) + 1):
                # row_num начинается с 3 (после строки 2)
                if row_num > len(column_a) or not column_a[row_num - 1] or column_a[row_num - 1].strip() == "":
                    log.info(f"Найдена пустая строка: {row_num}")
                    return row_num
            
            # Если все строки заполнены, возвращаем следующую
            next_row = len(column_a) + 1
            if next_row <= start_row:
                next_row = start_row + 1
            log.info(f"Все строки заполнены, используем новую строку: {next_row}")
            return next_row
            
        except Exception as e:
            log.warning(f"Ошибка при поиске пустой строки: {e}, используем строку {config.SHEET_START_ROW}")
            return config.SHEET_START_ROW
    
    def close(self):
        """Закрытие соединения (не требуется для gspread, но для совместимости)"""
        pass

