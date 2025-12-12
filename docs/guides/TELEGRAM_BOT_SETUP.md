# 🤖 Настройка Telegram бота

## Что сделать

### 1. Получить токен (2 минуты)
- Telegram → @BotFather → `/newbot` → имя → username → **скопировать токен**

### 2. Получить user_id (1 минута)
- Telegram → @userinfobot → `/start` → **скопировать user_id**

### 3. Скопировать саммари (5 минут)
```bash
python download_summaries.py
```
Или вручную: https://github.com/EvgeniyRibakov/ProductRadar/tree/testing-logs/logs/summaries

---

## Что мне нужно

Отправьте:
1. **Токен:** `1234567890:ABC...`
2. **Ваш user_id:** `123456789`
3. **Другие user_id** (если нужно): `987654321,555666777`

---

## После получения данных

Я создам бота → вы вставите данные в `.env` → запустим.

---

## Безопасность

- Не публикуйте токен
- `.env` уже в `.gitignore`
