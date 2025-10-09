"""
Тестовый скрипт для исследования Douyin API
Используется для ручного тестирования и анализа endpoints
"""

import asyncio
import aiohttp
import json
from datetime import datetime
from pathlib import Path


class DouyinResearcher:
    """Класс для исследования Douyin API"""
    
    def __init__(self):
        self.base_url = "https://www.douyin.com"
        self.session = None
        
        # Headers для имитации браузера
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ru;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.douyin.com/',
            'Origin': 'https://www.douyin.com',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }
        
        # Результаты исследования
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': []
        }
    
    async def init_session(self):
        """Инициализация HTTP сессии"""
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            timeout=timeout
        )
        print("✓ Сессия инициализирована")
    
    async def close_session(self):
        """Закрытие сессии"""
        if self.session:
            await self.session.close()
            print("✓ Сессия закрыта")
    
    async def test_main_page(self):
        """Тест 1: Проверка доступности главной страницы"""
        print("\n📍 Тест 1: Главная страница Douyin")
        test_result = {
            'test_name': 'main_page',
            'url': self.base_url,
            'success': False,
            'status_code': None,
            'notes': []
        }
        
        try:
            async with self.session.get(self.base_url) as response:
                test_result['status_code'] = response.status
                html = await response.text()
                
                if response.status == 200:
                    test_result['success'] = True
                    test_result['notes'].append(f"Страница доступна, размер: {len(html)} байт")
                    
                    # Проверяем наличие ключевых элементов
                    if 'login' in html.lower() or '登录' in html:
                        test_result['notes'].append("⚠️ Обнаружены элементы авторизации")
                    
                    if 'captcha' in html.lower() or '验证' in html:
                        test_result['notes'].append("⚠️ Возможна капча")
                    
                    print(f"  ✓ Статус: {response.status}")
                    print(f"  ✓ Размер HTML: {len(html)} байт")
                else:
                    test_result['notes'].append(f"Неожиданный статус: {response.status}")
                    print(f"  ✗ Статус: {response.status}")
        
        except Exception as e:
            test_result['notes'].append(f"Ошибка: {str(e)}")
            print(f"  ✗ Ошибка: {e}")
        
        self.results['tests'].append(test_result)
        return test_result
    
    async def test_search_endpoint(self, keyword: str = "护肤"):
        """Тест 2: Поиск по ключевому слову"""
        print(f"\n📍 Тест 2: Поиск по ключевому слову '{keyword}'")
        
        # Возможные варианты search endpoints (нужно протестировать)
        search_urls = [
            f"{self.base_url}/search/{keyword}",
            f"{self.base_url}/aweme/v1/web/search/item/?keyword={keyword}",
            f"{self.base_url}/aweme/v1/web/general/search/single/?keyword={keyword}",
        ]
        
        for url in search_urls:
            test_result = {
                'test_name': f'search_{keyword}',
                'url': url,
                'success': False,
                'status_code': None,
                'notes': []
            }
            
            print(f"\n  Пробую URL: {url}")
            
            try:
                async with self.session.get(url) as response:
                    test_result['status_code'] = response.status
                    content_type = response.headers.get('Content-Type', '')
                    
                    print(f"    Статус: {response.status}")
                    print(f"    Content-Type: {content_type}")
                    
                    if 'json' in content_type:
                        try:
                            data = await response.json()
                            test_result['success'] = True
                            test_result['response_sample'] = str(data)[:500]  # Первые 500 символов
                            print(f"    ✓ JSON ответ получен")
                            print(f"    Ключи: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                        except:
                            text = await response.text()
                            test_result['notes'].append(f"JSON parse error, text length: {len(text)}")
                    else:
                        text = await response.text()
                        test_result['notes'].append(f"HTML response, length: {len(text)}")
                        print(f"    HTML ответ, размер: {len(text)}")
            
            except Exception as e:
                test_result['notes'].append(f"Ошибка: {str(e)}")
                print(f"    ✗ Ошибка: {e}")
            
            self.results['tests'].append(test_result)
            
            # Небольшая задержка между запросами
            await asyncio.sleep(1)
    
    async def test_hashtag_search(self, hashtag: str = "发量"):
        """Тест 3: Поиск по хэштегу"""
        print(f"\n📍 Тест 3: Поиск по хэштегу #{hashtag}")
        
        search_query = f"#{hashtag}"
        
        test_result = {
            'test_name': f'hashtag_{hashtag}',
            'url': f"{self.base_url}/search/{search_query}",
            'success': False,
            'notes': []
        }
        
        try:
            async with self.session.get(test_result['url']) as response:
                test_result['status_code'] = response.status
                html = await response.text()
                
                print(f"  Статус: {response.status}")
                print(f"  Размер: {len(html)} байт")
                
                # Ищем JSON данные в HTML (часто встроены в <script> теги)
                if '"aweme' in html or '"video' in html:
                    test_result['notes'].append("Найдены упоминания video/aweme данных")
                    print(f"  ✓ Найдены данные о видео")
                
                test_result['success'] = response.status == 200
        
        except Exception as e:
            test_result['notes'].append(f"Ошибка: {str(e)}")
            print(f"  ✗ Ошибка: {e}")
        
        self.results['tests'].append(test_result)
    
    async def analyze_network_patterns(self):
        """Тест 4: Анализ сетевых паттернов"""
        print("\n📍 Тест 4: Анализ сетевых паттернов")
        print("""
        ⚠️ РУЧНОЙ ШАГ:
        
        1. Откройте браузер (Chrome/Firefox)
        2. Откройте DevTools (F12)
        3. Перейдите на вкладку Network
        4. Откройте https://www.douyin.com
        5. Выполните поиск по хэштегу #护肤
        6. Отфильтруйте по XHR/Fetch
        7. Найдите запросы с данными о видео
        8. Скопируйте:
           - Request URL
           - Request Headers
           - Response (первые 1000 символов)
        
        9. Вставьте данные в docs/research/douyin_research.md
           в раздел "API endpoints"
        
        Это критически важно для понимания реальной структуры API!
        """)
    
    def save_results(self):
        """Сохранение результатов исследования"""
        output_dir = Path("docs/research/results")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"douyin_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Результаты сохранены: {filepath}")
    
    async def run_all_tests(self):
        """Запуск всех тестов"""
        print("="*70)
        print("🔬 DOUYIN API RESEARCH - Автоматизированное тестирование")
        print("="*70)
        
        await self.init_session()
        
        try:
            # Тест 1: Главная страница
            await self.test_main_page()
            await asyncio.sleep(2)
            
            # Тест 2: Поиск
            await self.test_search_endpoint("护肤")
            await asyncio.sleep(2)
            
            # Тест 3: Хэштег
            await self.test_hashtag_search("发量")
            await asyncio.sleep(2)
            
            # Тест 4: Ручной анализ
            await self.analyze_network_patterns()
            
        finally:
            await self.close_session()
        
        # Сохраняем результаты
        self.save_results()
        
        print("\n" + "="*70)
        print("✓ Тестирование завершено!")
        print("="*70)
        print(f"\nВсего тестов: {len(self.results['tests'])}")
        success_count = sum(1 for t in self.results['tests'] if t['success'])
        print(f"Успешных: {success_count}/{len(self.results['tests'])}")
        print("\n📝 Следующий шаг: Проверьте результаты и выполните ручной анализ")
        print("   см. docs/research/douyin_research.md")


async def main():
    """Главная функция"""
    researcher = DouyinResearcher()
    await researcher.run_all_tests()


if __name__ == "__main__":
    print("\n🚀 Запуск исследования Douyin API...")
    print("⏱️  Ориентировочное время: 2-3 минуты\n")
    
    asyncio.run(main())


