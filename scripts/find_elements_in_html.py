"""
Скрипт для поиска элементов в HTML файле
Помогает найти нужные секции и классы для извлечения данных
"""

import re
from pathlib import Path
from bs4 import BeautifulSoup

def find_elements_in_html(html_file: str, search_terms: list):
    """Найти элементы в HTML по ключевым словам"""
    html_path = Path(html_file)
    if not html_path.exists():
        print(f"❌ Файл {html_file} не найден")
        return
    
    print(f"📄 Анализ файла: {html_file}\n")
    
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    for term in search_terms:
        print(f"\n{'='*60}")
        print(f"🔍 Поиск: '{term}'")
        print(f"{'='*60}\n")
        
        # Поиск по тексту
        text_matches = soup.find_all(string=re.compile(term, re.I))
        if text_matches:
            print(f"✅ Найдено {len(text_matches)} совпадений по тексту:")
            for i, match in enumerate(text_matches[:10], 1):  # Показываем первые 10
                parent = match.parent
                if parent:
                    print(f"\n  {i}. Текст: '{match.strip()[:100]}'")
                    print(f"     Тег: {parent.name}")
                    print(f"     Класс: {parent.get('class', 'нет')}")
                    print(f"     ID: {parent.get('id', 'нет')}")
                    print(f"     Родитель: {parent.parent.name if parent.parent else 'нет'}")
        
        # Поиск по классам
        class_matches = soup.find_all(class_=re.compile(term, re.I))
        if class_matches:
            print(f"\n✅ Найдено {len(class_matches)} элементов с классом, содержащим '{term}':")
            for i, match in enumerate(class_matches[:5], 1):  # Показываем первые 5
                print(f"\n  {i}. Тег: {match.name}")
                print(f"     Класс: {match.get('class', 'нет')}")
                print(f"     ID: {match.get('id', 'нет')}")
                print(f"     Текст (первые 100 символов): '{match.get_text()[:100]}'")
        
        # Поиск по ID
        id_matches = soup.find_all(id=re.compile(term, re.I))
        if id_matches:
            print(f"\n✅ Найдено {len(id_matches)} элементов с ID, содержащим '{term}':")
            for i, match in enumerate(id_matches[:5], 1):
                print(f"\n  {i}. Тег: {match.name}")
                print(f"     ID: {match.get('id', 'нет')}")
                print(f"     Класс: {match.get('class', 'нет')}")
                print(f"     Текст (первые 100 символов): '{match.get_text()[:100]}'")

if __name__ == "__main__":
    # Ищем последний HTML файл
    html_dir = Path("html_dumps")
    if html_dir.exists():
        html_files = list(html_dir.glob("*.html"))
        if html_files:
            latest_file = max(html_files, key=lambda p: p.stat().st_mtime)
            print(f"📁 Используется файл: {latest_file}\n")
            
            # Ключевые слова для поиска
            search_terms = [
                "Impression",
                "Script",
                "Hook",
                "Target Audience",
                "Audience",
                "Country",
                "First seen",
                "Data",
                "Script Analysis",
                "Hooks",
                "Scripts"
            ]
            
            find_elements_in_html(str(latest_file), search_terms)
        else:
            print("❌ HTML файлы не найдены в папке html_dumps/")
    else:
        print("❌ Папка html_dumps/ не найдена")








