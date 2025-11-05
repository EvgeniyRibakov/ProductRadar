#!/usr/bin/env python3
"""
Тестовый скрипт для проверки подключения к Google Sheets
"""

import os
import sys
from pathlib import Path

def test_google_sheets_connection():
    """Проверяет подключение к Google Sheets"""
    
    print("🔍 Проверка подключения к Google Sheets...")
    print("-" * 50)
    
    # Проверка наличия credentials файла
    credentials_path = Path("config/google-credentials.json")
    
    if not credentials_path.exists():
        print("❌ ОШИБКА: Файл credentials не найден!")
        print(f"   Ожидаемый путь: {credentials_path.absolute()}")
        print("\n📋 Инструкции:")
        print("   1. Следуйте инструкциям в config/README.md")
        print("   2. Создайте сервисный аккаунт в Google Cloud Console")
        print("   3. Скачайте JSON ключ и сохраните как google-credentials.json")
        return False
    
    print(f"✅ Файл credentials найден: {credentials_path.absolute()}")
    
    # Проверка установки библиотек
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        print("✅ Библиотеки установлены")
    except ImportError as e:
        print(f"❌ ОШИБКА: Библиотеки не установлены!")
        print(f"   Установите: pip install gspread google-auth google-auth-oauthlib")
        return False
    
    # Попытка подключения
    try:
        SCOPE = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=SCOPE
        )
        
        client = gspread.authorize(credentials)
        print("✅ Успешная авторизация")
        
        # Попытка открыть таблицу
        spreadsheet_id = "1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ"
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"✅ Таблица открыта: {spreadsheet.title}")
        
        # Попытка открыть лист
        sheet_name = "шаблон выгрузуи 1.0"
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
            print(f"✅ Лист найден: '{sheet_name}'")
            
            # Попытка прочитать данные
            test_cell = worksheet.acell("A1").value
            print(f"✅ Чтение данных работает (A1 = '{test_cell}')")
            
            print("\n" + "=" * 50)
            print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
            print("=" * 50)
            return True
            
        except gspread.exceptions.WorksheetNotFound:
            print(f"❌ ОШИБКА: Лист '{sheet_name}' не найден!")
            print(f"   Доступные листы: {[s.title for s in spreadsheet.worksheets()]}")
            return False
            
    except Exception as e:
        print(f"❌ ОШИБКА при подключении: {e}")
        print("\n📋 Возможные причины:")
        print("   1. Сервисный аккаунт не имеет доступа к таблице")
        print("   2. Google Sheets API не включен в проекте")
        print("   3. Неправильный формат credentials файла")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Google Sheets Connection Test")
    print("=" * 50)
    print()
    
    success = test_google_sheets_connection()
    
    sys.exit(0 if success else 1)

