@echo off
chcp 65001
echo === Пуш изменений в Git ===
echo.

echo 1. Проверка статуса...
git status
echo.

echo 2. Добавление изменений...
git add .
echo.

echo 3. Создание коммита...
git commit -m "feat: update project structure and documentation"
echo.

echo 4. Отправка на GitHub...
git push
echo.

echo ✅ Готово!
pause

