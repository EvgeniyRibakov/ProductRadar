"""
Утилита для анализа HTML дампов и поиска элементов по ориентирам
"""
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

def find_impressions_in_html(html_content: str) -> List[Dict[str, str]]:
    """
    Ищет impressions в HTML по структуре:
    <div class="data-count"><div class="item"><p class="value">33</p><p class="caption">Impression</p></div></div>
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    # Метод 1: Ищем через структуру div.data-count > div.item
    data_count_divs = soup.find_all('div', class_='data-count')
    for data_count in data_count_divs:
        items = data_count.find_all('div', class_='item')
        for item in items:
            caption = item.find('p', class_='caption')
            if caption and 'Impression' in caption.get_text():
                value_p = item.find('p', class_='value')
                if value_p:
                    value_text = value_p.get_text().strip()
                    results.append({
                        'method': 'DOM structure (data-count)',
                        'value': value_text,
                        'html': str(item)[:200]
                    })
    
    # Метод 2: Ищем div.name с текстом "Impression" и рядом div.value
    name_divs = soup.find_all('div', class_='name')
    for name_div in name_divs:
        name_text = name_div.get_text().strip()
        if 'Impression' in name_text:
            # Ищем родительский контейнер
            parent = name_div.parent
            if parent:
                value_div = parent.find('div', class_='value')
                if value_div:
                    value_text = value_div.get_text().strip()
                    results.append({
                        'method': 'DOM structure (div.name + div.value)',
                        'value': value_text,
                        'html': str(parent)[:200]
                    })
    
    return results

def find_script_hook_in_html(html_content: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Ищет Script и Hook в HTML по структуре:
    <span class="tit-text">Scripts</span> или <span class="tit-text">Hooks</span>
    с последующим <p class="content-text slot-wrap">
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = {'script': [], 'hook': []}
    
    # Ищем span.tit-text
    tit_text_spans = soup.find_all('span', class_='tit-text')
    for span in tit_text_spans:
        span_text = span.get_text().strip()
        
        # Ищем Script
        if 'Script' in span_text and 'Hook' not in span_text:
            # Ищем следующий p.content-text.slot-wrap
            parent = span.parent
            if parent:
                script_p = parent.find('p', class_='content-text slot-wrap')
                if script_p:
                    script_text = script_p.get_text().strip()
                    results['script'].append({
                        'method': 'span.tit-text (Scripts)',
                        'value': script_text[:100] + '...' if len(script_text) > 100 else script_text,
                        'html': str(parent)[:300]
                    })
        
        # Ищем Hook
        if 'Hook' in span_text:
            parent = span.parent
            if parent:
                hook_p = parent.find('p', class_='content-text slot-wrap')
                if hook_p:
                    hook_text = hook_p.get_text().strip()
                    results['hook'].append({
                        'method': 'span.tit-text (Hooks)',
                        'value': hook_text[:100] + '...' if len(hook_text) > 100 else hook_text,
                        'html': str(parent)[:300]
                    })
    
    return results

def find_audience_in_html(html_content: str) -> List[Dict[str, str]]:
    """
    Ищет Audience в HTML по структуре:
    <div class="audience-info-info">25-35...Android...</div>
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    audience_divs = soup.find_all('div', class_='audience-info-info')
    for div in audience_divs:
        text = div.get_text().strip()
        # Проверяем на "All"
        if 'All' in text:
            results.append({
                'method': 'div.audience-info-info (All)',
                'value': 'All',
                'html': str(div)[:200]
            })
        # Ищем возраст
        age_match = re.search(r'(\d{1,2}-\d{1,2})', text)
        if age_match:
            results.append({
                'method': 'div.audience-info-info (age)',
                'value': age_match.group(1),
                'html': str(div)[:200]
            })
    
    return results

def find_country_in_html(html_content: str) -> List[Dict[str, str]]:
    """
    Ищет Country в HTML по структуре:
    <div class="name">Country/Region</div> рядом с <div class="el-tooltip ellipsis">Philippines</div>
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    name_divs = soup.find_all('div', class_='name')
    for name_div in name_divs:
        name_text = name_div.get_text().strip()
        if 'Country' in name_text or 'Страна' in name_text:
            parent = name_div.parent
            if parent:
                country_div = parent.find('div', class_='el-tooltip ellipsis')
                if country_div:
                    country_text = country_div.get_text().strip()
                    results.append({
                        'method': 'div.name (Country) + div.el-tooltip.ellipsis',
                        'value': country_text,
                        'html': str(parent)[:200]
                    })
    
    return results

def find_first_seen_in_html(html_content: str) -> List[Dict[str, str]]:
    """
    Ищет First seen в HTML по структуре:
    <div class="name">First seen - Last seen</div> рядом с <div class="value">Nov 07 2025 ~ Nov 13 2025</div>
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    results = []
    
    name_divs = soup.find_all('div', class_='name')
    for name_div in name_divs:
        name_text = name_div.get_text().strip()
        if 'First seen' in name_text:
            parent = name_div.parent
            if parent:
                value_div = parent.find('div', class_='value')
                if value_div:
                    value_text = value_div.get_text().strip()
                    # Извлекаем первую дату
                    date_match = re.search(r'([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})', value_text)
                    if date_match:
                        results.append({
                            'method': 'div.name (First seen) + div.value',
                            'value': date_match.group(1),
                            'html': str(parent)[:200]
                        })
    
    return results

def analyze_html_dump(file_path: Path):
    """
    Анализирует HTML дамп и ищет все нужные элементы
    """
    print(f"\n{'='*80}")
    print(f"Анализ файла: {file_path.name}")
    print(f"{'='*80}\n")
    
    html_content = file_path.read_text(encoding='utf-8')
    
    # Ищем impressions
    print("📊 IMPRESSIONS:")
    impressions = find_impressions_in_html(html_content)
    if impressions:
        for i, imp in enumerate(impressions, 1):
            print(f"  {i}. Метод: {imp['method']}")
            print(f"     Значение: {imp['value']}")
            print(f"     HTML: {imp['html'][:150]}...")
    else:
        print("  ❌ Не найдено")
    
    # Ищем Script и Hook
    print("\n📝 SCRIPT & HOOK:")
    script_hook = find_script_hook_in_html(html_content)
    if script_hook['script']:
        print("  Script:")
        for i, script in enumerate(script_hook['script'], 1):
            print(f"    {i}. Метод: {script['method']}")
            print(f"       Значение: {script['value'][:80]}...")
    else:
        print("  Script: ❌ Не найдено")
    
    if script_hook['hook']:
        print("  Hook:")
        for i, hook in enumerate(script_hook['hook'], 1):
            print(f"    {i}. Метод: {hook['method']}")
            print(f"       Значение: {hook['value'][:80]}...")
    else:
        print("  Hook: ❌ Не найдено")
    
    # Ищем Audience
    print("\n👥 AUDIENCE:")
    audience = find_audience_in_html(html_content)
    if audience:
        for i, aud in enumerate(audience, 1):
            print(f"  {i}. Метод: {aud['method']}")
            print(f"     Значение: {aud['value']}")
    else:
        print("  ❌ Не найдено")
    
    # Ищем Country
    print("\n🌍 COUNTRY:")
    country = find_country_in_html(html_content)
    if country:
        for i, cnt in enumerate(country, 1):
            print(f"  {i}. Метод: {cnt['method']}")
            print(f"     Значение: {cnt['value']}")
    else:
        print("  ❌ Не найдено")
    
    # Ищем First seen
    print("\n📅 FIRST SEEN:")
    first_seen = find_first_seen_in_html(html_content)
    if first_seen:
        for i, fs in enumerate(first_seen, 1):
            print(f"  {i}. Метод: {fs['method']}")
            print(f"     Значение: {fs['value']}")
    else:
        print("  ❌ Не найдено")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    # Ищем последний HTML дамп
    html_dir = Path("html_dumps")
    if not html_dir.exists():
        print("❌ Директория html_dumps не найдена")
        exit(1)
    
    # Получаем все HTML файлы, отсортированные по времени
    html_files = sorted(html_dir.glob("ad_search_*.html"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not html_files:
        print("❌ HTML дампы не найдены")
        exit(1)
    
    # Анализируем последний файл
    latest_file = html_files[0]
    analyze_html_dump(latest_file)
    
    # Спрашиваем, анализировать ли все файлы
    if len(html_files) > 1:
        print(f"\nНайдено {len(html_files)} HTML файлов. Анализировать все? (y/n): ", end="")
        # Для автоматизации просто анализируем последний
        # response = input()
        # if response.lower() == 'y':
        #     for file in html_files:
        #         analyze_html_dump(file)






