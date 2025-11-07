#!/usr/bin/env python3
"""
Скрипт для записи "тест" в Google Sheets
"""

import sys
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    print("❌ ОШИБКА: Библиотеки не установлены!")
    print("   Установите: pip install gspread google-auth google-auth-oauthlib")
    sys.exit(1)

def write_test_to_sheets():
    """Записывает 'тест' в Google Sheets"""
    
    print("📝 Запись 'тест' в Google Sheets...")
    print("-" * 50)
    
    # Путь к credentials
    credentials_path = Path("config/google-credentials.json")
    
    if not credentials_path.exists():
        print(f"❌ ОШИБКА: Файл credentials не найден: {credentials_path.absolute()}")
        return False
    
    try:
        # Настройка credentials
        SCOPE = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        
        credentials = Credentials.from_service_account_file(
            str(credentials_path),
            scopes=SCOPE
        )
        
        # Подключение к таблице
        client = gspread.authorize(credentials)
        spreadsheet_id = "1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ"
        spreadsheet = client.open_by_key(spreadsheet_id)
        print(f"✅ Таблица открыта: {spreadsheet.title}")
        
        # Открытие листа
        sheet_name = "шаблон выгрузуи 1.0"
        worksheet = spreadsheet.worksheet(sheet_name)
        print(f"✅ Лист найден: '{sheet_name}'")
        
        # Запись "тест" в ячейку (используем ячейку, которая не используется - например Z100)
        # Или можно в A1 для проверки, но лучше в безопасное место
        test_cell = "Z100"  # Безопасная ячейка, которая не используется
        worksheet.update_acell(test_cell, "тест")  # Используем update_acell для одной ячейки
        print(f"✅ Записано 'тест' в ячейку {test_cell}")
        
        # Проверка записи
        value = worksheet.acell(test_cell).value
        if value == "тест":
            print(f"✅ Проверка: значение в {test_cell} = '{value}'")
            print("\n" + "=" * 50)
            print("✅ УСПЕШНО! 'тест' записан в таблицу")
            print("=" * 50)
            return True
        else:
            print(f"❌ ОШИБКА: Ожидалось 'тест', получено '{value}'")
            return False
            
    except gspread.exceptions.APIError as e:
        print(f"❌ ОШИБКА API: {e}")
        if "PERMISSION_DENIED" in str(e):
            print("\n📋 Решение:")
            print("   1. Откройте таблицу: https://docs.google.com/spreadsheets/d/1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ")
            print("   2. Нажмите 'Поделиться'")
            print(f"   3. Добавьте email: ai-agent-sheets@ai-agent-sheets-473515.iam.gserviceaccount.com")
            print("   4. Дайте права 'Редактор'")
        return False
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("Запись 'тест' в Google Sheets")
    print("=" * 50)
    print()
    
    success = write_test_to_sheets()
    sys.exit(0 if success else 1)


