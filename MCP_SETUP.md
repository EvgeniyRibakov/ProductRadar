# Настройка MCP для Google Sheets

## Текущая конфигурация

MCP сервер для Google Sheets добавлен в `mcp.json`. Если официальный пакет `@modelcontextprotocol/server-google-sheets` не существует, используйте альтернативный подход ниже.

## Вариант 1: Через официальный MCP сервер (если доступен)

Конфигурация уже добавлена в `c:\Users\Acer\.cursor\mcp.json`:

```json
"google-sheets": {
  "command": "npx",
  "args": ["-y", "@modelcontextprotocol/server-google-sheets"],
  "env": {
    "GOOGLE_SHEETS_CREDENTIALS_PATH": "C:\\Users\\Acer\\Downloads\\ProductRadar-main\\ProductRadar-main\\config\\google-credentials.json",
    "GOOGLE_SHEETS_SPREADSHEET_ID": "1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ"
  }
}
```

## Вариант 2: Через Python библиотеки (рекомендуется)

Если MCP сервер недоступен, используйте прямой доступ через Google Sheets API в Python коде:

### Шаг 1: Установите зависимости

```bash
pip install gspread google-auth google-auth-oauthlib google-auth-httplib2
```

### Шаг 2: Настройте credentials

Следуйте инструкциям в `config/README.md` для создания `google-credentials.json`

### Шаг 3: Использование в коде

```python
import gspread
from google.oauth2.service_account import Credentials

# Настройка credentials
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

credentials = Credentials.from_service_account_file(
    "config/google-credentials.json",
    scopes=SCOPE
)

# Подключение к таблице
client = gspread.authorize(credentials)
spreadsheet = client.open_by_key("1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ")
worksheet = spreadsheet.worksheet("шаблон выгрузуи 1.0")

# Запись данных
worksheet.update("A3", [[1, "Product Name", ...]])
```

## Вариант 3: Использование переменных окружения

Если MCP сервер использует переменные окружения, убедитесь, что они установлены:

```bash
# Windows PowerShell
$env:GOOGLE_SHEETS_CREDENTIALS_PATH = "C:\Users\Acer\Downloads\ProductRadar-main\ProductRadar-main\config\google-credentials.json"
$env:GOOGLE_SHEETS_SPREADSHEET_ID = "1VJMixODvnIPBf7EjFoJ8XMH1lepycVlXREKQI7MVxWQ"
```

## Проверка работы

После настройки:

1. Перезапустите Cursor
2. Проверьте, что MCP сервер загружается без ошибок
3. Попробуйте использовать функции MCP для работы с Google Sheets

## Если возникают проблемы

1. Проверьте, что файл `google-credentials.json` существует в `config/`
2. Убедитесь, что сервисный аккаунт имеет доступ к таблице
3. Проверьте, что Google Sheets API включен в Google Cloud Console
4. Посмотрите логи MCP сервера в Cursor

## Дополнительные ресурсы

- [Google Sheets API Documentation](https://developers.google.com/sheets/api)
- [gspread Documentation](https://docs.gspread.org/)
- [MCP Documentation](https://modelcontextprotocol.io/)

