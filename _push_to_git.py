#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для автоматического коммита и пуша изменений в Git"""

import subprocess
import sys

def run_git_command(command):
    """Выполнить git команду"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.returncode == 0
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def main():
    print("=== Пуш изменений в Git ===\n")
    
    # 1. Проверяем статус
    print("1. Проверка статуса...")
    run_git_command("git status")
    
    # 2. Добавляем все изменения
    print("\n2. Добавление изменений...")
    if not run_git_command("git add ."):
        print("Ошибка при добавлении файлов")
        return 1
    
    # 3. Коммитим
    print("\n3. Создание коммита...")
    commit_message = "feat: update project structure and documentation"
    if not run_git_command(f'git commit -m "{commit_message}"'):
        print("Нет изменений для коммита или ошибка")
    
    # 4. Пушим
    print("\n4. Отправка на GitHub...")
    if not run_git_command("git push"):
        print("Ошибка при пуше")
        return 1
    
    print("\n✅ Готово! Изменения отправлены в GitHub")
    return 0

if __name__ == "__main__":
    sys.exit(main())

