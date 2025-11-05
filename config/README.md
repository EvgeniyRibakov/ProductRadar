# Конфигурация Google Sheets API

## Шаги для настройки:

### 1. Создание проекта в Google Cloud Console

1. Перейдите на https://console.cloud.google.com/
2. Создайте новый проект или выберите существующий
3. Назовите проект (например: "ProductRadar")

### 2. Включение Google Sheets API

1. В Google Cloud Console перейдите в "APIs & Services" > "Library"
2. Найдите "Google Sheets API"
3. Нажмите "Enable" (Включить)

### 3. Создание сервисного аккаунта

1. Перейдите в "APIs & Services" > "Credentials"
2. Нажмите "Create Credentials" > "Service Account"
3. Заполните:
   - Service account name: `productradar-sheets`
   - Service account ID: `productradar-sheets` (автозаполнение)
4. Нажмите "Create and Continue"
5. Пропустите шаг "Grant access" (опционально)
6. Нажмите "Done"

### 4. Создание ключа для сервисного аккаунта

1. В списке сервисных аккаунтов найдите созданный аккаунт
2. Нажмите на него
3. Перейдите на вкладку "Keys"
4. Нажмите "Add Key" > "Create new key"
5. Выберите формат "JSON"
6. Нажмите "Create"
7. Файл автоматически скачается

### 5. Сохранение credentials

1. Переименуйте скачанный JSON-файл в `google-credentials.json`
2. Переместите его в папку `config/` этого проекта
3. **ВАЖНО:** Не коммитьте этот файл в Git!

### 6. Предоставление доступа к Google Таблице

1. Откройте файл `google-credentials.json`
2. Найдите поле `client_email` (например: `productradar-sheets@your-project.iam.gserviceaccount.com`)
3. Откройте вашу Google Таблицу:
   - https://docs.google.com/spreadsheets/d/1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ
4. Нажмите "Поделиться" (Share)
5. Вставьте email из `client_email`
6. Дайте права "Редактор" (Editor)
7. Нажмите "Отправить"

### 7. Проверка настроек

После выполнения всех шагов структура должна быть:
```
config/
  └── google-credentials.json  (ваш JSON файл с ключами)
```

## Альтернативный вариант (OAuth2)

Если нужен OAuth2 вместо сервисного аккаунта:
1. Создайте OAuth 2.0 Client ID в Google Cloud Console
2. Скачайте credentials в формате JSON
3. Сохраните как `google-credentials.json` в папке `config/`

## Безопасность

- ⚠️ **НИКОГДА не коммитьте `google-credentials.json` в Git!**
- Добавьте в `.gitignore`: `config/google-credentials.json`
- Держите файл в безопасности и не передавайте третьим лицам

