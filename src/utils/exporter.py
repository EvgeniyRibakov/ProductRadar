"""Экспорт данных в CSV и загрузка на Google Drive"""

import csv
from datetime import datetime
from typing import List
from pathlib import Path
import io

from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

from src.models.product import Product, ProductCollection
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


class CSVExporter:
    """Класс для экспорта продуктов в CSV"""
    
    # Порядок колонок согласно спецификации
    CSV_COLUMNS = [
        'Дата обнаружения',
        'Платформа',
        'Категория',
        'Название товара',
        'Ссылка на товар',
        'Ссылка на продавца',
        'Цена',
        'Всего просмотров',
        'просмотров за 24 часа',
        'комментариев за 24 часа',
        'ER, %',
        'Доля пользовательского контента, %',
        'Возраст листинга, дни',
        'Коротко о пиках по хэштегам',
        'Топ-хуки',
        'Топ-офферы',
        'Почему это работает',
        'Риски (претензии/интеллектуальная собственность)',
        'Воспроизводимость, 0–10',
        'Простота выборки, 0–10',
        'trendScore, 0–100',
        'Приоритет',
        'Статус',
        'Ответственный',
        'Скрин/доказательство (URL)'
    ]
    
    @staticmethod
    def export_to_csv(
        products: List[Product],
        output_path: str = None
    ) -> str:
        """
        Экспорт продуктов в CSV файл
        
        Args:
            products: Список продуктов
            output_path: Путь для сохранения (если None, генерируется автоматически)
            
        Returns:
            Путь к созданному файлу
        """
        if output_path is None:
            timestamp = datetime.now().strftime('%Y-%m-%d_%H%M')
            output_path = f"radar_{timestamp}.csv"
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=CSVExporter.CSV_COLUMNS)
                
                # Записываем заголовки
                writer.writeheader()
                
                # Записываем данные продуктов
                for product in products:
                    row = product.to_csv_row()
                    writer.writerow(row)
            
            logger.info(f"CSV файл создан: {output_path} ({len(products)} продуктов)")
            return output_path
            
        except Exception as e:
            logger.error(f"Ошибка при создании CSV: {e}")
            raise
    
    @staticmethod
    def export_to_memory(products: List[Product]) -> io.StringIO:
        """
        Экспорт продуктов в строковый буфер (для загрузки без сохранения на диск)
        
        Args:
            products: Список продуктов
            
        Returns:
            StringIO объект с CSV данными
        """
        output = io.StringIO()
        
        writer = csv.DictWriter(output, fieldnames=CSVExporter.CSV_COLUMNS)
        writer.writeheader()
        
        for product in products:
            row = product.to_csv_row()
            writer.writerow(row)
        
        output.seek(0)
        return output


class GoogleDriveUploader:
    """Класс для загрузки файлов на Google Drive"""
    
    def __init__(
        self, 
        credentials_path: str = None,
        folder_id: str = "1fGCUHtUmNZlJyTjmbLmPjcfeOrDu9icq"
    ):
        """
        Инициализация загрузчика
        
        Args:
            credentials_path: Путь к файлу с credentials
            folder_id: ID папки на Google Drive
        """
        self.folder_id = folder_id
        self.credentials_path = credentials_path
        self.service = None
    
    def authenticate(self) -> None:
        """Аутентификация в Google Drive API"""
        try:
            if self.credentials_path:
                # Используем service account
                creds = ServiceAccountCredentials.from_service_account_file(
                    self.credentials_path,
                    scopes=['https://www.googleapis.com/auth/drive.file']
                )
            else:
                logger.warning("Credentials не предоставлены, Google Drive недоступен")
                return
            
            self.service = build('drive', 'v3', credentials=creds)
            logger.info("Аутентификация в Google Drive успешна")
            
        except Exception as e:
            logger.error(f"Ошибка аутентификации Google Drive: {e}")
            raise
    
    def upload_file(
        self, 
        file_path: str = None,
        file_content: io.StringIO = None,
        filename: str = None
    ) -> str:
        """
        Загрузка файла на Google Drive
        
        Args:
            file_path: Путь к локальному файлу
            file_content: Содержимое файла в памяти
            filename: Имя файла (если используется file_content)
            
        Returns:
            ID загруженного файла
        """
        if not self.service:
            self.authenticate()
        
        if not self.service:
            raise Exception("Google Drive service недоступен")
        
        try:
            # Подготовка метаданных
            if file_path:
                filename = Path(file_path).name
            elif not filename:
                filename = f"radar_{datetime.now().strftime('%Y-%m-%d_%H%M')}.csv"
            
            file_metadata = {
                'name': filename,
                'parents': [self.folder_id]
            }
            
            # Подготовка медиа
            if file_path:
                media = MediaIoBaseUpload(
                    open(file_path, 'rb'),
                    mimetype='text/csv',
                    resumable=True
                )
            elif file_content:
                # Конвертируем StringIO в BytesIO для загрузки
                content_bytes = file_content.getvalue().encode('utf-8')
                media = MediaIoBaseUpload(
                    io.BytesIO(content_bytes),
                    mimetype='text/csv',
                    resumable=True
                )
            else:
                raise ValueError("Необходимо указать file_path или file_content")
            
            # Загрузка
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Файл загружен на Google Drive: {filename} (ID: {file_id})")
            
            return file_id
            
        except HttpError as e:
            logger.error(f"HTTP ошибка при загрузке на Google Drive: {e}")
            raise
        except Exception as e:
            logger.error(f"Ошибка при загрузке на Google Drive: {e}")
            raise
    
    def get_file_url(self, file_id: str) -> str:
        """
        Получение URL файла
        
        Args:
            file_id: ID файла на Google Drive
            
        Returns:
            URL для просмотра файла
        """
        return f"https://drive.google.com/file/d/{file_id}/view"


class ProductExporter:
    """Комплексный экспортер продуктов"""
    
    def __init__(
        self, 
        google_credentials_path: str = None,
        google_folder_id: str = "1fGCUHtUmNZlJyTjmbLmPjcfeOrDu9icq"
    ):
        """
        Инициализация экспортера
        
        Args:
            google_credentials_path: Путь к credentials для Google Drive
            google_folder_id: ID папки на Google Drive
        """
        self.csv_exporter = CSVExporter()
        self.drive_uploader = GoogleDriveUploader(
            credentials_path=google_credentials_path,
            folder_id=google_folder_id
        )
    
    def export_and_upload(
        self, 
        products: List[Product],
        save_locally: bool = True,
        upload_to_drive: bool = True
    ) -> dict:
        """
        Экспорт в CSV и загрузка на Google Drive
        
        Args:
            products: Список продуктов
            save_locally: Сохранить локально
            upload_to_drive: Загрузить на Google Drive
            
        Returns:
            Словарь с информацией о результатах
        """
        result = {
            'local_path': None,
            'drive_file_id': None,
            'drive_url': None,
            'product_count': len(products)
        }
        
        try:
            # Локальное сохранение
            if save_locally:
                local_path = self.csv_exporter.export_to_csv(products)
                result['local_path'] = local_path
                logger.info(f"Локальный файл создан: {local_path}")
            
            # Загрузка на Google Drive
            if upload_to_drive:
                # Экспортируем в память
                file_content = self.csv_exporter.export_to_memory(products)
                
                # Загружаем
                file_id = self.drive_uploader.upload_file(
                    file_content=file_content
                )
                
                result['drive_file_id'] = file_id
                result['drive_url'] = self.drive_uploader.get_file_url(file_id)
                
                logger.info(f"Файл загружен на Google Drive: {result['drive_url']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте и загрузке: {e}")
            raise

