# 🔐 Настройка локальных файлов

Эти файлы **НЕ хранятся в Git** и должны быть переданы локально при переносе проекта на новое устройство.

---

## 📋 Список файлов для передачи

### 1. `config/google-credentials.json` ⚠️ ОБЯЗАТЕЛЬНО

**Что это:** JSON-файл с ключами для доступа к Google Sheets API

**Как получить:**
1. Перейдите на https://console.cloud.google.com/
2. Выберите проект (или создайте новый)
3. Включите Google Sheets API:
   - "APIs & Services" > "Library" > найдите "Google Sheets API" > "Enable"
4. Создайте Service Account:
   - "APIs & Services" > "Credentials" > "Create Credentials" > "Service Account"
   - Название: `productradar-sheets`
   - Нажмите "Create and Continue" > "Done"
5. Создайте ключ:
   - Откройте созданный Service Account > "Keys" > "Add Key" > "Create new key" > "JSON"
   - Файл автоматически скачается
6. Сохраните файл:
   - Переименуйте в `google-credentials.json`
   - Переместите в папку `config/`

**Структура файла:**
```json
{
  "type": "service_account",
  "project_id": "ваш-проект",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "productradar-sheets@...iam.gserviceaccount.com",
  ...
}
```

**Важно:**
- Не публикуйте этот файл в Git!
- Не передавайте через незащищенные каналы
- Храните в безопасном месте

---

### 2. `config/.env` ⚠️ ОБЯЗАТЕЛЬНО

**Что это:** Файл с переменными окружения (пароли, токены, ID)

**Как создать:**
1. Скопируйте шаблон:
   ```bash
   cp config/.env_sample config/.env
   ```

2. Откройте `config/.env` и заполните:

```env
# Учетные данные Pipiads
PIPIADS_EMAIL=ваш_email@example.com
PIPIADS_PASSWORD=ваш_пароль

# Google Sheets
GOOGLE_SHEETS_ID=1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ
GOOGLE_SHEETS_SHEET_NAME=шаблон выгрузуи 1.0

# Telegram Bot (опционально, если используете бота)
TG_API_TOKEN=ваш_токен_бота
ID_TG=ваш_user_id

# Для нескольких пользователей Telegram:
# ID_TG=963382703,123456789,987654321
```

**Где взять значения:**

- **PIPIADS_EMAIL / PIPIADS_PASSWORD:** Учетные данные для входа на pipiads.com
- **GOOGLE_SHEETS_ID:** ID таблицы из URL (после `/d/` и до следующего `/`)
- **GOOGLE_SHEETS_SHEET_NAME:** Название листа в таблице (обычно "шаблон выгрузуи 1.0")
- **TG_API_TOKEN:** Токен бота от @BotFather (если используете Telegram бота)
- **ID_TG:** Ваш Telegram user_id (получить через @userinfobot)

**Важно:**
- Не ставьте пробелы вокруг знака `=`
- Не используйте кавычки вокруг значений
- Не публикуйте этот файл в Git!

---

### 3. `config/cookies.json` (опционально)

**Что это:** Cookies для авторизации на Pipiads

**Как получить:**
- Создается автоматически при первом запуске парсера
- Можно скопировать с другого устройства, чтобы не авторизовываться заново

**Структура файла:**
```json
[
  {
    "name": "session_id",
    "value": "...",
    "domain": ".pipiads.com",
    ...
  }
]
```

**Когда использовать:**
- Если хотите сохранить сессию между запусками
- Если не хотите авторизовываться каждый раз

**Важно:**
- Cookies могут устареть (обычно действуют несколько дней/недель)
- Если авторизация не работает, удалите файл и авторизуйтесь заново

---

## 📦 Как передать файлы на новое устройство

### Вариант 1: Через USB/облако (рекомендуется)

1. Скопируйте файлы с текущего устройства:
   - `config/google-credentials.json`
   - `config/.env`
   - `config/cookies.json` (если есть)

2. Переместите на новое устройство (USB, облако, email)

3. Поместите в правильные папки:
   ```
   ProductRadar/
   └── config/
       ├── google-credentials.json  ← скопировать сюда
       ├── .env                     ← скопировать сюда
       └── cookies.json             ← скопировать сюда (опционально)
   ```

### Вариант 2: Через зашифрованный архив

1. Создайте ZIP-архив с паролем:
   ```bash
   # Windows (PowerShell)
   Compress-Archive -Path config\google-credentials.json,config\.env -DestinationPath config_backup.zip -CompressionLevel Optimal
   ```

2. Отправьте архив через безопасный канал

3. Распакуйте на новом устройстве

### Вариант 3: Пересоздать файлы

Если нет доступа к старым файлам:

1. **google-credentials.json:** Создайте новый Service Account (см. выше)
2. **.env:** Заполните вручную (см. выше)
3. **cookies.json:** Будет создан автоматически при первом запуске

---

## ✅ Проверка после передачи

После передачи файлов проверьте:

1. **Файлы на месте:**
   ```bash
   # Windows
   dir config\google-credentials.json
   dir config\.env
   
   # Linux/Mac
   ls config/google-credentials.json
   ls config/.env
   ```

2. **Проверка подключения к Google Sheets:**
   ```bash
   python tests/test_google_sheets.py
   ```
   
   Должно вывести: ✅ Подключение успешно

3. **Проверка переменных окружения:**
   ```bash
   python tests/test_env_reading.py
   ```
   
   Должны отобразиться все переменные (без значений паролей)

---

## 🔒 Безопасность

### Что НЕ делать:

❌ Не коммитьте эти файлы в Git  
❌ Не отправляйте через незащищенные каналы (обычный email, мессенджеры)  
❌ Не публикуйте в открытых репозиториях  
❌ Не делитесь файлами с посторонними  

### Что делать:

✅ Используйте зашифрованные каналы передачи  
✅ Храните файлы в безопасном месте  
✅ Используйте разные учетные данные для разных окружений  
✅ Регулярно обновляйте пароли и токены  

---

## 🆘 Если файлы потеряны

### `google-credentials.json` потерян:

1. Создайте новый Service Account в Google Cloud Console
2. Скачайте новый JSON-ключ
3. Сохраните как `config/google-credentials.json`
4. Добавьте `client_email` в Google Таблицу с правами "Редактор"

### `.env` потерян:

1. Скопируйте `config/.env_sample` в `config/.env`
2. Заполните все переменные вручную
3. Получите недостающие данные (токены, пароли)

### `cookies.json` потерян:

- Не критично — файл создастся автоматически при первом запуске
- Просто авторизуйтесь заново на Pipiads

---

## 📝 Чек-лист передачи на новое устройство

- [ ] `config/google-credentials.json` скопирован
- [ ] `config/.env` создан и заполнен
- [ ] `config/cookies.json` скопирован (опционально)
- [ ] Файлы размещены в правильных папках
- [ ] Проверка подключения к Google Sheets прошла успешно
- [ ] Проверка переменных окружения прошла успешно

---

**Готово!** Теперь можно запускать проект на новом устройстве. 🚀

