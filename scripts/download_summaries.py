"""
Скрипт для скачивания файлов саммари с GitHub
"""

import requests
import json
from pathlib import Path

# Настройки
GITHUB_REPO = "EvgeniyRibakov/ProductRadar"
BRANCH = "testing-logs"
SUMMARIES_PATH = "logs/summaries"
LOCAL_SUMMARIES_DIR = Path("logs/summaries")

def get_github_files():
    """Получить список файлов из папки summaries на GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{SUMMARIES_PATH}"
    params = {"ref": BRANCH}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при получении списка файлов: {e}")
        return None

def download_file(file_info):
    """Скачать файл с GitHub"""
    download_url = file_info.get("download_url")
    file_name = file_info.get("name")
    
    if not download_url or not file_name:
        print(f"⚠️ Пропущен файл: нет download_url или name")
        return False
    
    # Пропускаем README.md (он уже есть)
    if file_name == "README.md":
        print(f"⏭️ Пропущен {file_name} (уже существует)")
        return True
    
    try:
        response = requests.get(download_url)
        response.raise_for_status()
        
        file_path = LOCAL_SUMMARIES_DIR / file_name
        file_path.write_text(response.text, encoding="utf-8")
        print(f"✅ Скачан: {file_name}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при скачивании {file_name}: {e}")
        return False

def main():
    """Основная функция"""
    print("=" * 60)
    print("📥 Скачивание файлов саммари с GitHub")
    print("=" * 60)
    print()
    
    # Создаем папку если её нет
    LOCAL_SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Папка: {LOCAL_SUMMARIES_DIR}")
    print()
    
    # Получаем список файлов
    print("🔍 Получение списка файлов с GitHub...")
    files = get_github_files()
    
    if not files:
        print("❌ Не удалось получить список файлов")
        print()
        print("💡 Альтернатива: скопируйте файлы вручную из:")
        print(f"   https://github.com/{GITHUB_REPO}/tree/{BRANCH}/{SUMMARIES_PATH}")
        print(f"   в папку: {LOCAL_SUMMARIES_DIR}")
        return
    
    if not isinstance(files, list):
        print("❌ Неожиданный формат ответа от GitHub API")
        return
    
    print(f"✅ Найдено файлов: {len(files)}")
    print()
    
    # Скачиваем файлы
    print("📥 Начало скачивания...")
    print()
    
    downloaded = 0
    skipped = 0
    errors = 0
    
    for file_info in files:
        if file_info.get("type") != "file":
            continue
        
        if download_file(file_info):
            downloaded += 1
        else:
            errors += 1
    
    print()
    print("=" * 60)
    print("📊 Результаты:")
    print(f"   ✅ Скачано: {downloaded}")
    print(f"   ⏭️ Пропущено: {skipped}")
    print(f"   ❌ Ошибок: {errors}")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ Прервано пользователем")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()


