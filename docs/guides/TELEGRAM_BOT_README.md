# 🤖 Telegram бот для ProductRadar

## Запуск

```bash
python run_telegram_bot.py
```

## Настройка

1. **Токен и user_id** в `config/.env`:
   ```
   TG_API_TOKEN=ваш_токен
   ID_TG=ваш_user_id
   ```

2. **Настройки парсера** в `config/bot_settings.json`:
   ```json
   {
     "min_products": 3,
     "max_products_to_check": 15,
     "min_impressions": 1000,
     "days_back": 60,
     "headless": true
   }
   ```

## Функции

- **🔄 Запустить парсер** — выбор количества товаров (3/5/10/25)
- **📊 Просмотр саммари** — список последних итераций
- **⚙️ Настройки** — просмотр текущих настроек
- **📈 Статус** — текущее состояние парсера
- **🛑 Остановить парсер** — принудительная остановка

## Установка библиотек

```bash
pip install -r requirements.txt
```

## Структура

- `src/telegram_bot.py` — основной бот
- `src/parser_runner.py` — запуск парсера
- `src/summary_manager.py` — работа с саммари
- `src/bot_config.py` — конфигурация
- `run_telegram_bot.py` — точка входа


