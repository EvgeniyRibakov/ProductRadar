# Инструкция по настройке проекта ProductRadar

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/YOUR_USERNAME/ProductRadar.git
cd ProductRadar
```

### 2. Установка Python
Убедитесь, что у вас установлен Python 3.10 или выше:
```bash
python --version
```

### 3. Вариант А: Использование Poetry (рекомендуется)

#### Установка Poetry
```bash
# Windows (PowerShell)
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -

# Linux/MacOS
curl -sSL https://install.python-poetry.org | python3 -
```

#### Настройка проекта
```bash
# Создать виртуальное окружение в папке проекта
poetry config virtualenvs.in-project true

# Установить зависимости
poetry install

# Активировать окружение
poetry shell
```

### 4. Вариант Б: Использование pip и venv

```bash
# Создать виртуальное окружение
python -m venv venv

# Активировать окружение
# Windows
.\venv\Scripts\activate
# Linux/MacOS
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt
```

### 5. Настройка переменных окружения

Скопируйте файл `.env.example` в `.env`:
```bash
# Windows
copy .env.example .env
# Linux/MacOS
cp .env.example .env
```

Отредактируйте `.env` и добавьте ваши API ключи:
```env
OPENAI_API_KEY=your_actual_api_key_here
ANTHROPIC_API_KEY=your_actual_api_key_here
```

### 6. Проверка установки

Запустите тесты:
```bash
# С Poetry
poetry run pytest tests/

# С pip
pytest tests/
```

## 📁 Структура проекта

```
ProductRadar/
├── .github/                    # GitHub workflows и шаблоны
│   ├── workflows/
│   │   └── ci.yml             # CI/CD pipeline
│   ├── ISSUE_TEMPLATE/        # Шаблоны для issues
│   └── PULL_REQUEST_TEMPLATE.md
├── src/                       # Исходный код
│   ├── agents/               # AI агенты
│   │   ├── __init__.py
│   │   └── base_agent.py     # Базовый класс агента
│   ├── models/               # ML модели
│   ├── utils/                # Утилиты
│   │   ├── __init__.py
│   │   └── logger.py         # Логирование
│   └── config/               # Конфигурация
│       ├── __init__.py
│       └── settings.py       # Настройки приложения
├── tests/                    # Тесты
│   ├── __init__.py
│   └── test_base_agent.py
├── data/                     # Данные
│   ├── raw/                  # Сырые данные
│   └── processed/            # Обработанные данные
├── notebooks/                # Jupyter notebooks
├── scripts/                  # Скрипты
│   └── run_agent.py         # Запуск агента
├── docs/                     # Документация
├── logs/                     # Логи
├── .env.example              # Пример файла с переменными окружения
├── .gitignore               # Git ignore
├── pyproject.toml           # Poetry конфигурация
├── requirements.txt         # Pip зависимости
├── README.md                # Документация проекта
├── CONTRIBUTING.md          # Руководство для контрибьюторов
├── LICENSE                  # Лицензия
├── Makefile                 # Makefile с полезными командами
└── .flake8                  # Конфигурация линтера
```

## 🛠️ Полезные команды

### С использованием Makefile
```bash
make install    # Установить зависимости
make test       # Запустить тесты
make lint       # Проверить код
make format     # Отформатировать код
make clean      # Очистить временные файлы
make run        # Запустить агента
```

### С использованием Poetry
```bash
poetry install              # Установить зависимости
poetry run pytest          # Запустить тесты
poetry run black .         # Форматировать код
poetry run flake8 .        # Линтинг
poetry add package_name    # Добавить пакет
```

### С использованием pip
```bash
pip install -r requirements.txt    # Установить зависимости
pytest tests/                      # Запустить тесты
black src/ tests/                  # Форматировать код
flake8 src/ tests/                 # Линтинг
```

## 🔧 Настройка IDE

### VSCode
Рекомендуемые расширения:
- Python
- Pylance
- Python Test Explorer
- GitLens

### PyCharm
1. Откройте проект
2. Settings → Project → Python Interpreter
3. Выберите Poetry environment или venv

## 📝 Git Workflow

### Работа с ветками
```bash
# Создать новую ветку
git checkout -b feature/your-feature

# Зафиксировать изменения
git add .
git commit -m "feat: описание изменений"

# Отправить на GitHub
git push origin feature/your-feature
```

### Синхронизация с основной веткой
```bash
git checkout main
git pull origin main
git checkout feature/your-feature
git merge main
```

## 🐛 Решение проблем

### Проблемы с Poetry
```bash
# Очистить кэш Poetry
poetry cache clear pypi --all

# Переустановить окружение
poetry env remove python
poetry install
```

### Проблемы с виртуальным окружением
```bash
# Удалить и создать заново
rm -rf venv/
python -m venv venv
```

### Конфликты зависимостей
```bash
# Обновить pip
pip install --upgrade pip

# Переустановить зависимости
pip install -r requirements.txt --upgrade
```

## 📞 Поддержка

Если у вас возникли проблемы:
1. Проверьте [Issues](https://github.com/YOUR_USERNAME/ProductRadar/issues)
2. Создайте новый issue с подробным описанием
3. Свяжитесь с мейнтейнерами

## 📚 Дополнительные ресурсы

- [Poetry Documentation](https://python-poetry.org/docs/)
- [Python Packaging Guide](https://packaging.python.org/)
- [Git Documentation](https://git-scm.com/doc)

