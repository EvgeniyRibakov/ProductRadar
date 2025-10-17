# Альтернативный план без дорогого PiPiAds API

## 🎯 Проблема
PiPiAds API стоит минимум $2000/мес - слишком дорого для старта.

## ✅ Решение: Гибридный подход

### Архитектура
```
Apify TikTok Scraper → Свой мини-парсер → GPT-4 Analyzer → Weekly Reports
      ($49/мес)         (прокси $20/мес)     ($20-50/мес)
```

---

## 📋 План реализации

### **Этап 1: Apify TikTok Scraper (неделя 1)**

**Стоимость:** $49/мес (Starter план)

**Что делаем:**
1. Регистрируемся на Apify.com
2. Используем готовый актор "TikTok Scraper"
3. Парсим trending видео по beauty хэштегам:
   - #beautyproducts
   - #skincare
   - #haircare
   - #beautytiktok
   - #tiktokmademebuyit

**Что получаем:**
```json
{
  "video_id": "7123456789",
  "author": "@beautyguru",
  "description": "Amazing hair growth serum! 🔥",
  "views": 2500000,
  "likes": 450000,
  "comments": 12000,
  "shares": 3500,
  "created_at": "2024-10-15",
  "hashtags": ["#haircare", "#hairgrowth"],
  "video_url": "https://tiktok.com/@beautyguru/video/7123456789"
}
```

**Код для запуска:**
```python
from apify_client import ApifyClient

client = ApifyClient("your_api_token")

# Запуск актора
run_input = {
    "hashtags": ["beautyproducts", "skincare", "haircare"],
    "resultsPerPage": 50,
    "shouldDownloadVideos": False,  # не скачиваем видео, только метаданные
    "shouldDownloadCovers": True
}

run = client.actor("clockworks/tiktok-scraper").call(run_input=run_input)

# Получение результатов
for item in client.dataset(run["defaultDatasetId"]).iterate_items():
    print(f"Video: {item['text']}, Views: {item['playCount']}")
```

**Ограничения:**
- Нет прямых данных о продуктах TikTok Shop
- Нет метрик продаж
- Нужно вручную определять какие видео про продукты

---

### **Этап 2: Свой мини-парсер для TikTok Shop (неделя 2-3)**

**Стоимость:** $20-30/мес (только прокси)

**Что делаем:**
1. Для каждого trending видео проверяем есть ли ссылка на TikTok Shop
2. Если есть - извлекаем данные о продукте
3. Собираем базовые метрики

**Технический стек:**
```bash
pip install playwright playwright-stealth
playwright install chromium
```

**Код парсера:**
```python
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import asyncio

async def parse_tiktok_shop_product(product_url):
    """
    Парсинг конкретного продукта из TikTok Shop
    """
    async with async_playwright() as p:
        # Запуск браузера с прокси
        browser = await p.chromium.launch(
            headless=True,
            proxy={
                "server": "http://your-proxy.com:8080",
                "username": "user",
                "password": "pass"
            }
        )
        
        page = await browser.new_page()
        await stealth_async(page)  # Обход детекции
        
        try:
            # Переход на страницу продукта
            await page.goto(product_url, wait_until="networkidle")
            
            # Извлечение данных
            product_data = await page.evaluate("""
                () => {
                    return {
                        name: document.querySelector('[data-testid="product-title"]')?.textContent,
                        price: document.querySelector('[data-testid="product-price"]')?.textContent,
                        rating: document.querySelector('[data-testid="product-rating"]')?.textContent,
                        sold_count: document.querySelector('[data-testid="sold-count"]')?.textContent,
                        // Можем добавить больше селекторов
                    }
                }
            """)
            
            await browser.close()
            return product_data
            
        except Exception as e:
            print(f"Ошибка при парсинге {product_url}: {e}")
            await browser.close()
            return None

# Использование
async def main():
    product_url = "https://shop.tiktok.com/view/product/..."
    data = await parse_tiktok_shop_product(product_url)
    print(data)

asyncio.run(main())
```

**Что нужно:**
- Rotating прокси ($20-30/мес) - например BrightData, Oxylabs starter
- User-agent rotation
- Случайные задержки между запросами

**Риски:**
- Может потребоваться обновление селекторов при изменениях TikTok
- Возможны блокировки (решается через прокси)

---

### **Этап 3: Data Pipeline (неделя 3)**

**Объединяем данные:**

```python
# src/data_collector/hybrid_collector.py

from apify_client import ApifyClient
import asyncio
from typing import List, Dict

class HybridDataCollector:
    """
    Собирает данные из Apify + свой парсер
    """
    
    def __init__(self, apify_token: str):
        self.apify_client = ApifyClient(apify_token)
        
    async def collect_weekly_data(self) -> List[Dict]:
        """
        Еженедельный сбор данных
        """
        print("📥 Шаг 1: Сбор trending видео из Apify...")
        
        # 1. Получаем trending видео по beauty хэштегам
        trending_videos = self._get_trending_videos_from_apify()
        
        print(f"   ✓ Найдено {len(trending_videos)} trending видео")
        
        # 2. Фильтруем только видео с продуктами
        videos_with_products = self._filter_videos_with_products(trending_videos)
        
        print(f"   ✓ Из них {len(videos_with_products)} с продуктами")
        
        # 3. Для каждого видео извлекаем данные о продукте
        print("\n📦 Шаг 2: Сбор данных о продуктах...")
        
        products = []
        for video in videos_with_products[:50]:  # Ограничим 50 для начала
            product_url = self._extract_product_url(video)
            
            if product_url:
                # Используем свой парсер
                product_data = await parse_tiktok_shop_product(product_url)
                
                if product_data:
                    # Объединяем данные видео + продукта
                    products.append({
                        "product": product_data,
                        "video": {
                            "views": video["playCount"],
                            "likes": video["diggCount"],
                            "comments": video["commentCount"],
                            "url": video["webVideoUrl"]
                        }
                    })
        
        print(f"   ✓ Собрано данных о {len(products)} продуктах")
        
        return products
    
    def _get_trending_videos_from_apify(self) -> List[Dict]:
        """Получение trending видео через Apify"""
        
        run_input = {
            "hashtags": [
                "beautyproducts",
                "skincare", 
                "haircare",
                "beautytiktok",
                "tiktokmademebuyit"
            ],
            "resultsPerPage": 100,
            "shouldDownloadVideos": False
        }
        
        run = self.apify_client.actor("clockworks/tiktok-scraper").call(
            run_input=run_input
        )
        
        items = list(
            self.apify_client.dataset(run["defaultDatasetId"]).iterate_items()
        )
        
        return items
    
    def _filter_videos_with_products(self, videos: List[Dict]) -> List[Dict]:
        """Фильтр: только видео где есть ссылка на продукт"""
        
        filtered = []
        for video in videos:
            description = video.get("text", "").lower()
            
            # Проверяем есть ли признаки продукта
            if any(keyword in description for keyword in [
                "shop now", "link in bio", "buy", "purchase", 
                "product", "shop.tiktok"
            ]):
                filtered.append(video)
        
        return filtered
    
    def _extract_product_url(self, video: Dict) -> str:
        """Извлечение ссылки на продукт из видео"""
        
        # TikTok часто содержит ссылки в описании или в профиле
        # Это упрощённая версия, нужно будет доработать
        
        description = video.get("text", "")
        
        # Поиск прямой ссылки
        import re
        match = re.search(r'shop\.tiktok\.com/[\w-]+', description)
        
        if match:
            return f"https://{match.group()}"
        
        # Иначе нужно будет парсить профиль автора
        return None
```

---

### **Этап 4: AI Analyzer (неделя 4)**

**Используем те же модули что планировали:**

1. **Trend Detector** - анализ динамики роста
2. **Likato Fit Analyzer** - GPT-4 оценка соответствия бренду
3. **SSR Tester** - тестирование на виртуальных покупателях

**Код остаётся тот же из TECHNICAL_ROADMAP_MVP.md**

---

## 💰 Бюджет (реальный)

### Первый месяц:
- **Apify Starter:** $49
- **Прокси:** $20-30 (например Bright Data Starter)
- **OpenAI API:** $20-50
- **VPS (опционально):** $5-10
- **ИТОГО: $94-139/мес** (~8,500-12,500₽)

### Сравнение с PiPiAds:
| Вариант | Стоимость | Качество данных | Сложность |
|---------|-----------|-----------------|-----------|
| PiPiAds API | $2000/мес | ⭐⭐⭐⭐⭐ | Легко |
| Наш гибрид | $100-140/мес | ⭐⭐⭐⭐ | Средне |
| Свой парсер | $30-50/мес | ⭐⭐⭐ | Сложно |

**Экономия: ~$1900/мес ($22,800/год)** 🎉

---

## ⚠️ Ограничения и компромиссы

### Что теряем vs PiPiAds:
1. ❌ Нет прямого доступа ко всем продуктам TikTok Shop
2. ❌ Нет оценок продаж (revenue estimates)
3. ❌ Нужно самим связывать видео → продукты
4. ❌ Меньше покрытие (не все продукты найдём)

### Что сохраняем:
1. ✅ Trending видео с метриками (views, likes)
2. ✅ Можем найти популярные продукты
3. ✅ AI анализ и ранжирование
4. ✅ Автоматизация

### Как компенсировать:
- Фокус на **самых вирусных видео** (топ 1% по views)
- Использовать **несколько хэштегов** для полноты
- **Ручная валидация** топ-10 продуктов перед отчётом

---

## 🚀 Quick Start

### День 1: Настройка Apify
```bash
# 1. Регистрация на apify.com
# 2. Получить API token
# 3. Установить клиент
pip install apify-client

# 4. Тест
python -c "
from apify_client import ApifyClient
client = ApifyClient('YOUR_TOKEN')
print('✅ Apify работает!')
"
```

### День 2-3: Тест парсинга
```bash
# 1. Установить Playwright
pip install playwright playwright-stealth
playwright install

# 2. Тест парсера
python src/test_parser.py
```

### Неделя 2: Интеграция
- Объединить Apify + свой парсер
- Сохранение в SQLite
- Первый сбор данных

### Неделя 3-4: AI модули
- Trend Detector
- Likato Fit Analyzer
- Orchestrator

### Неделя 5: Автоматизация
- Еженедельный запуск
- Генерация отчётов

---

## 🎯 Метрики успеха

### Первый месяц:
- ✅ Собирать минимум 30-50 продуктов/неделю
- ✅ 70%+ найденных продуктов релевантны beauty категории
- ✅ Система работает без падений

### Через 3 месяца:
- ✅ База данных 300-500 продуктов
- ✅ Можем отслеживать динамику трендов
- ✅ Минимум 1 идея пошла в R&D

---

## 🔄 План миграции (если захочется улучшить)

### Через 6 месяцев можно:

1. **Добавить больше источников:**
   - Instagram Reels (через Apify)
   - YouTube Shorts beauty trends
   - Reddit beauty communities

2. **Улучшить свой парсер:**
   - Добавить больше TikTok Shop данных
   - Автоматический поиск продуктов по скриншотам (ML)

3. **Купить PiPiAds если появится бюджет:**
   - Использовать как дополнительный источник
   - Проверка качества своих данных

---

## ❓ FAQ

**Q: Достаточно ли данных из Apify?**
A: Для начала - да. Тренды beauty хорошо представлены через хэштеги.

**Q: Насколько сложно поддерживать парсер?**
A: Селекторы могут меняться раз в 1-2 месяца. Займёт 2-4 часа на обновление.

**Q: Можно ли без прокси?**
A: Теоретически да, но высок риск блокировки. Лучше взять дешёвые.

**Q: Apify не заблокирует TikTok?**
A: Apify использует свои прокси и anti-detection, обычно работает стабильно.

---

## 📞 Следующие шаги

1. ✅ Зарегистрироваться на Apify (есть бесплатный trial)
2. ✅ Протестировать TikTok Scraper актор
3. ✅ Оценить качество получаемых данных
4. ✅ Если OK → начать разработку гибридной системы

---

**Готов начинать? Давай сначала протестируем Apify на реальных данных!** 🚀

