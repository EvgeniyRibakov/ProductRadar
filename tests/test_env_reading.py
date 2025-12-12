"""
Тестовый скрипт для проверки чтения .env файла
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src import bot_config

print("=" * 60)
print("Тест чтения .env файла")
print("=" * 60)
print()

print(f"Путь к .env: {bot_config.ENV_FILE}")
print(f"Файл существует: {bot_config.ENV_FILE.exists()}")
print()

if bot_config.ENV_FILE.exists():
    print("Содержимое файла:")
    print("-" * 60)
    with open(bot_config.ENV_FILE, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            print(f"{i}: {repr(line)}")
    print("-" * 60)
    print()

# Загружаем переменные
from src.bot_config import load_env_file
env_vars = load_env_file()

print(f"Загружено переменных: {len(env_vars)}")
print(f"Ключи: {list(env_vars.keys())}")
print()

for key, value in env_vars.items():
    print(f"  {key} = '{value}' (длина: {len(value)})")
print()

print("Проверка значений:")
print(f"  TG_API_TOKEN: '{bot_config.TELEGRAM_BOT_TOKEN}' (длина: {len(bot_config.TELEGRAM_BOT_TOKEN)})")
print(f"  ID_TG: '{bot_config.TELEGRAM_ALLOWED_USERS}'")
print()

is_valid, error = bot_config.validate_config()
if is_valid:
    print("✅ Конфигурация валидна")
else:
    print(f"❌ Ошибка: {error}")


