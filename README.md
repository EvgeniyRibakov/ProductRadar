# 📊 ProductRadar - Мониторинг Beauty-трендов в TikTok Shop

Автоматизированная система для мониторинга beauty-трендов в TikTok Shop. Проект собирает данные о товарах и рекламных видео с сайта Pipiads и автоматически заполняет Google Таблицы.

**Для кого:** Компания Likato (Cosmo Beauty Ltd) — производитель натуральной косметики для волос, тела и лица.

---

## 📋 Содержание

- [Быстрый старт](#-быстрый-старт)
- [Структура проекта](#-структура-проекта)
- [Установка на новое устройство](#-установка-на-новое-устройство)
- [Локальные файлы (не в Git)](#-локальные-файлы-не-в-git)
- [Запуск проекта](#-запуск-проекта)
- [Документация](#-документация)

---

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/EvgeniyRibakov/ProductRadar.git
cd ProductRadar
```

### 2. Установка зависимостей

```bash
# Установка Python библиотек
pip install -r requirements.txt

# Установка браузера для Playwright
playwright install chromium
```

### 3. Настройка локальных файлов

**⚠️ ВАЖНО:** Эти файлы не хранятся в Git и должны быть переданы локально:

1. **`config/google-credentials.json`** — ключи для Google Sheets API
2. **`config/.env`** — переменные окружения (см. `config/.env_sample`)
3. **`config/cookies.json`** — cookies для авторизации (опционально)

Подробнее: [Локальные файлы](#-локальные-файлы-не-в-git)

### 4. Запуск

```bash
# Запуск парсера
python tests/test_parser_engine.py

# Запуск Telegram бота
python run_telegram_bot.py
```

---

## 📁 Структура проекта

```
ProductRadar/
├── src/                    # Основной код проекта
│   ├── browser_manager.py # Управление браузером
│   ├── parser_engine.py   # Парсинг данных
│   ├── sheets_writer.py   # Запись в Google Sheets
│   ├── telegram_bot.py    # Telegram бот
│   └── ...
│
├── tests/                  # Тесты и скрипты запуска
│   ├── test_parser_engine.py  # Главный скрипт парсера
│   └── ...
│
├── scripts/                # Вспомогательные скрипты
│   ├── download_summaries.py
│   └── ...
│
├── config/                 # Конфигурация
│   ├── .env_sample        # Шаблон переменных окружения
│   ├── google-credentials.json  # ⚠️ Не в Git!
│   └── .env               # ⚠️ Не в Git!
│
├── docs/                   # Документация
│   ├── guides/            # Руководства
│   └── reference/         # Справочники
│
├── examples/               # Примеры HTML страниц
├── logs/                   # Логи и саммари
├── archive/                # Архивные файлы
└── requirements.txt       # Зависимости Python
```

---

## 💻 Установка на новое устройство

### Шаг 1: Установка Python

1. Скачайте Python 3.8+ с https://www.python.org/downloads/
2. **ВАЖНО:** При установке поставьте галочку **"Add Python to PATH"**
3. Проверьте установку:
   ```bash
   python --version
   ```

### Шаг 2: Клонирование проекта

```bash
git clone https://github.com/EvgeniyRibakov/ProductRadar.git
cd ProductRadar
```

### Шаг 3: Установка зависимостей

```bash
# Установка библиотек
pip install -r requirements.txt

# Установка браузера для автоматизации
playwright install chromium
```

### Шаг 4: Настройка Google Sheets API

1. Перейдите на https://console.cloud.google.com/
2. Создайте проект или выберите существующий
3. Включите **Google Sheets API**:
   - "APIs & Services" > "Library" > найдите "Google Sheets API" > "Enable"
4. Создайте **Service Account**:
   - "APIs & Services" > "Credentials" > "Create Credentials" > "Service Account"
   - Название: `productradar-sheets`
5. Создайте ключ:
   - Откройте Service Account > "Keys" > "Add Key" > "Create new key" > "JSON"
   - Файл скачается автоматически
6. Сохраните ключ:
   - Переименуйте файл в `google-credentials.json`
   - Переместите в папку `config/`
7. Предоставьте доступ к таблице:
   - Откройте `config/google-credentials.json`
   - Найдите `client_email` (например: `productradar-sheets@project.iam.gserviceaccount.com`)
   - Откройте таблицу: https://docs.google.com/spreadsheets/d/1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ
   - Нажмите "Поделиться" → вставьте `client_email` → права "Редактор" → "Отправить"

Подробнее: `docs/guides/QUICK_START.md`

### Шаг 5: Настройка переменных окружения

1. Скопируйте шаблон:
   ```bash
   cp config/.env_sample config/.env
   ```

2. Откройте `config/.env` и заполните:
   ```env
   PIPIADS_EMAIL=ваш_email@example.com
   PIPIADS_PASSWORD=ваш_пароль
   GOOGLE_SHEETS_ID=1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ
   GOOGLE_SHEETS_SHEET_NAME=шаблон выгрузуи 1.0
   TG_API_TOKEN=ваш_токен_бота  # Для Telegram бота
   ID_TG=ваш_user_id            # Для Telegram бота
   ```

### Шаг 6: Проверка подключения

```bash
# Проверка Google Sheets
python tests/test_google_sheets.py
```

Если видите ✅ — всё готово!

---

## 🔐 Локальные файлы (не в Git)

Эти файлы **НЕ хранятся в Git** и должны быть переданы локально при переносе проекта:

### 1. `config/google-credentials.json`

**Что это:** Ключи для доступа к Google Sheets API

**Как получить:**
- См. [Шаг 4: Настройка Google Sheets API](#шаг-4-настройка-google-sheets-api)

**Где хранить:** `config/google-credentials.json`

### 2. `config/.env`

**Что это:** Переменные окружения (пароли, токены, ID)

**Как создать:**
```bash
cp config/.env_sample config/.env
# Затем отредактируйте config/.env
```

**Содержимое:**
```env
PIPIADS_EMAIL=ваш_email@example.com
PIPIADS_PASSWORD=ваш_пароль
GOOGLE_SHEETS_ID=1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ
GOOGLE_SHEETS_SHEET_NAME=шаблон выгрузуи 1.0
TG_API_TOKEN=ваш_токен_бота
ID_TG=ваш_user_id
```

### 3. `config/cookies.json` (опционально)

**Что это:** Cookies для авторизации на Pipiads (создаются автоматически при первом запуске)

**Как передать:** Скопируйте файл с другого устройства

---

## ▶️ Запуск проекта

### Запуск парсера

```bash
python tests/test_parser_engine.py
```

**Что происходит:**
1. Открывается браузер (может быть невидимым в headless режиме)
2. Проект входит в аккаунт Pipiads
3. Начинается сбор данных о товарах и видео
4. Данные записываются в Google Таблицу

**Время выполнения:** 5-15 минут (зависит от количества данных)

### Запуск Telegram бота

```bash
python run_telegram_bot.py
```

**Требования:**
- Настроен `config/.env` с `TG_API_TOKEN` и `ID_TG`
- Бот создан через @BotFather

Подробнее: `docs/guides/TELEGRAM_BOT_SETUP.md`

---

## 📚 Документация

### Руководства (docs/guides/)

- **QUICK_START.md** — быстрый старт с Google Sheets
- **QUICK_START_BOT.md** — быстрый старт Telegram бота
- **TELEGRAM_BOT_SETUP.md** — подробная настройка бота
- **HOW_TO_CHECK_PARSER.md** — как проверить работу парсера

### Справочники (docs/reference/)

- **TECHNICAL_PLAN.md** — технический план проекта
- **TZ_DETAILED.md** — детальное техническое задание
- **VIDEO_CARDS_STRUCTURE.md** — структура карточек видео
- **ALGORITHM_SUMMARY.md** — описание алгоритма работы

---

## 🔧 Решение проблем

### "python is not recognized"

**Решение:**
- Убедитесь, что Python установлен
- При установке должна быть поставлена галочка "Add Python to PATH"
- Перезапустите терминал

### "pip is not recognized"

**Решение:**
```bash
python -m pip install -r requirements.txt
```

### Ошибка доступа к Google Таблице

**Решение:**
1. Проверьте, что `config/google-credentials.json` существует
2. Убедитесь, что email из credentials добавлен в таблицу с правами "Редактор"
3. Проверьте, что Google Sheets API включен в Google Cloud Console

### Браузер не открывается / Playwright ошибки

**Решение:**
```bash
playwright install chromium
# Или принудительно:
playwright install --force chromium
```

---

## 📋 Полезные команды

```bash
# Проверка версии Python
python --version

# Проверка подключения к Google Sheets
python tests/test_google_sheets.py

# Тест браузера
python tests/test_browser_manager.py

# Запуск основного парсера
python tests/test_parser_engine.py

# Запуск Telegram бота
python run_telegram_bot.py
```

---

## ✅ Чек-лист готовности

Перед запуском проекта убедитесь, что:

- [ ] Python установлен (проверено `python --version`)
- [ ] Проект клонирован с GitHub
- [ ] Все библиотеки установлены (`pip install -r requirements.txt`)
- [ ] Браузер Playwright установлен (`playwright install chromium`)
- [ ] Google Sheets API настроен
- [ ] Файл `config/google-credentials.json` существует
- [ ] Сервисный аккаунт имеет доступ к Google Таблице
- [ ] Файл `config/.env` создан и заполнен
- [ ] Тест подключения к Google Sheets прошёл успешно

**Если все пункты отмечены — можно запускать проект!** 🚀

---

## 📝 Лицензия

Этот проект создан для компании Likato (Cosmo Beauty Ltd).

---

**Удачи в работе с проектом!** 🎉

Если у вас возникли вопросы или проблемы — создайте Issue на GitHub: https://github.com/EvgeniyRibakov/ProductRadar/issues
