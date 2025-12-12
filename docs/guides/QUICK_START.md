# 🚀 Быстрый старт - Настройка Google Sheets MCP

## Шаг 1: Настройка Google Cloud Console (5 минут)

1. Перейдите на https://console.cloud.google.com/
2. Создайте проект или выберите существующий
3. Включите **Google Sheets API**:
   - "APIs & Services" > "Library" > найдите "Google Sheets API" > "Enable"
4. Создайте **Service Account**:
   - "APIs & Services" > "Credentials" > "Create Credentials" > "Service Account"
   - Название: `productradar-sheets`
   - Нажмите "Create and Continue" > "Done"
5. Создайте ключ:
   - Откройте созданный Service Account > "Keys" > "Add Key" > "Create new key" > "JSON"
   - Файл автоматически скачается

## Шаг 2: Сохранение credentials (1 минута)

1. Переименуйте скачанный файл в `google-credentials.json`
2. Переместите его в папку `config/` проекта:
   ```
   config/google-credentials.json
   ```

## Шаг 3: Предоставление доступа к таблице (1 минута)

1. Откройте `config/google-credentials.json`
2. Найдите `client_email` (например: `productradar-sheets@project.iam.gserviceaccount.com`)
3. Откройте таблицу: https://docs.google.com/spreadsheets/d/1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ
4. Нажмите "Поделиться" → вставьте `client_email` → дайте права "Редактор" → "Отправить"

## Шаг 4: Установка зависимостей (1 минута)

```bash
pip install -r requirements.txt
```

## Шаг 5: Проверка подключения (30 секунд)

```bash
python test_google_sheets.py
```

Если видите ✅ - все готово!

## Шаг 6: Перезапуск Cursor

1. Закройте Cursor полностью
2. Откройте заново
3. MCP сервер Google Sheets должен автоматически подключиться

## ✅ Готово!

Теперь вы можете использовать MCP для работы с Google Sheets в проекте.

## 🤖 Запуск Telegram бота

```bash
python run_telegram_bot.py
```

## 📋 Полезные ссылки

- Подробная инструкция: `config/README.md`
- Настройка MCP: `MCP_SETUP.md`
- Технический план: `TECHNICAL_PLAN.md`

## ❓ Если что-то не работает

1. Проверьте, что файл `config/google-credentials.json` существует
2. Убедитесь, что сервисный аккаунт имеет доступ к таблице
3. Проверьте, что Google Sheets API включен
4. Запустите `python test_google_sheets.py` для диагностики

