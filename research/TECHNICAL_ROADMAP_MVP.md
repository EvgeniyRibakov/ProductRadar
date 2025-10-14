# Технический роудмап MVP: ИИ-агент для ProductRadar

## 🎯 Концепция MVP

**Идея:** Гибридная система = PiPiAds (данные) + ИИ-агент (анализ)

```
PiPiAds API → Data Pipeline → AI Analyzer → Ranked Opportunities → Weekly Report
     ↓              ↓              ↓                ↓                    ↓
   Сырые        Очистка      Умный анализ    Топ идей для      Email/Dashboard
   данные       данных       с LLM           производства
```

### Преимущества такого подхода:
- ✅ **Быстрый старт** - данные есть сразу (3-5 дней)
- ✅ **Стабильность** - PiPiAds сам поддерживает парсинг
- ✅ **Фокус на ценности** - разрабатываем анализ, а не парсинг
- ✅ **Применяем SSR** - можем тестировать концепты через LLM
- ✅ **Масштабируемость** - позже добавим свой парсер если нужно

---

## 📊 Интеграция с PiPiAds

### Что такое PiPiAds?

**PiPiAds** - сервис аналитики TikTok/Facebook рекламы и TikTok Shop:
- 📺 Мониторит вирусные видео и объявления
- 🛍️ Отслеживает продукты TikTok Shop
- 📈 Предоставляет метрики (просмотры, продажи, лайки)
- 🌍 Покрывает US, UK, SEA (Thailand, Vietnam, Philippines)
- 🔌 Есть API для автоматизации

**Тарифы:**
- **Basic** - $99/мес (до 100 запросов/день)
- **Pro** - $199/мес (до 500 запросов/день) 
- **Enterprise** - $299/мес (неограниченно + приоритет)

**Рекомендация для старта:** Pro ($199/мес) - достаточно для ежедневного сбора

### Как работает PiPiAds API

**Эндпоинты для нашей задачи:**

#### 1. Поиск трендовых продуктов
```python
GET /api/v1/tiktok-shop/products/trending
Params:
  - region: "US" | "TH" | "VN" | "PH" | "UK"
  - category: "Beauty & Personal Care"
  - sort_by: "views" | "sales" | "engagement"
  - time_range: "7d" | "14d" | "30d"
  - limit: 50

Response:
{
  "products": [
    {
      "id": "tts_12345",
      "name": "CeraVe Hydrating Facial Cleanser",
      "price": 14.99,
      "category": "Skincare",
      "shop_url": "https://shop.tiktok.com/...",
      "metrics": {
        "views": 2500000,
        "sales": 15000,
        "revenue_estimate": 224850,
        "engagement_rate": 8.5,
        "video_count": 450  // количество видео с продуктом
      },
      "trend_status": "rising",  // rising | stable | declining
      "first_seen": "2024-10-01",
      "images": ["url1", "url2"]
    }
  ]
}
```

#### 2. Данные по конкретному продукту
```python
GET /api/v1/tiktok-shop/product/{product_id}
Params:
  - include_videos: true  // получить топ видео с продуктом
  - include_history: true // историю метрик

Response:
{
  "product": {...},
  "videos": [
    {
      "video_id": "vid_123",
      "creator": "@beautyguru",
      "views": 500000,
      "likes": 45000,
      "comments": 1200,
      "created_at": "2024-10-10",
      "video_url": "https://tiktok.com/@beautyguru/video/123"
    }
  ],
  "metrics_history": [
    {"date": "2024-10-07", "views": 2000000, "sales": 12000},
    {"date": "2024-10-14", "views": 2500000, "sales": 15000}
  ]
}
```

#### 3. Поиск по ключевым словам
```python
GET /api/v1/tiktok-shop/search
Params:
  - query: "hair growth serum"
  - region: "US"
  - category: "Beauty & Personal Care"

Response: список продуктов
```

### План интеграции

**Этап 1: Настройка доступа (1 день)**
```python
# 1. Регистрация на pipiads.com
# 2. Покупка тарифа Pro ($199/мес)
# 3. Получение API ключа
# 4. Тестирование доступа

import requests

PIPIADS_API_KEY = "your_key_here"
BASE_URL = "https://api.pipiads.com/v1"

headers = {
    "Authorization": f"Bearer {PIPIADS_API_KEY}",
    "Content-Type": "application/json"
}

# Тест запрос
response = requests.get(
    f"{BASE_URL}/tiktok-shop/products/trending",
    headers=headers,
    params={
        "region": "US",
        "category": "Beauty & Personal Care",
        "sort_by": "views",
        "time_range": "7d",
        "limit": 50
    }
)

products = response.json()["products"]
print(f"Получено продуктов: {len(products)}")
```

**Этап 2: Data Pipeline (2-3 дня)**

Создать модуль для сбора и нормализации данных:

```python
# src/data_collector/pipiads_client.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

@dataclass
class Product:
    """Модель продукта"""
    id: str
    name: str
    price: float
    category: str
    region: str
    shop_url: str
    
    # Метрики
    views: int
    sales: int
    revenue_estimate: float
    engagement_rate: float
    video_count: int
    
    # Тренд
    trend_status: str  # rising | stable | declining
    first_seen: datetime
    
    # Дополнительно
    images: List[str]
    description: Optional[str] = None

class PiPiAdsClient:
    """Клиент для работы с PiPiAds API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.pipiads.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_trending_products(
        self, 
        region: str = "US",
        category: str = "Beauty & Personal Care",
        time_range: str = "7d",
        limit: int = 50
    ) -> List[Product]:
        """Получить трендовые продукты"""
        
        response = requests.get(
            f"{self.base_url}/tiktok-shop/products/trending",
            headers=self.headers,
            params={
                "region": region,
                "category": category,
                "sort_by": "views",
                "time_range": time_range,
                "limit": limit
            }
        )
        
        data = response.json()
        return [self._parse_product(p) for p in data["products"]]
    
    def get_product_details(self, product_id: str) -> dict:
        """Получить детальную информацию о продукте"""
        
        response = requests.get(
            f"{self.base_url}/tiktok-shop/product/{product_id}",
            headers=self.headers,
            params={
                "include_videos": True,
                "include_history": True
            }
        )
        
        return response.json()
    
    def search_products(self, query: str, region: str = "US") -> List[Product]:
        """Поиск продуктов по ключевым словам"""
        
        response = requests.get(
            f"{self.base_url}/tiktok-shop/search",
            headers=self.headers,
            params={
                "query": query,
                "region": region,
                "category": "Beauty & Personal Care"
            }
        )
        
        data = response.json()
        return [self._parse_product(p) for p in data["products"]]
    
    def _parse_product(self, raw: dict) -> Product:
        """Парсинг сырых данных в модель Product"""
        return Product(
            id=raw["id"],
            name=raw["name"],
            price=raw["price"],
            category=raw["category"],
            region=raw.get("region", "US"),
            shop_url=raw["shop_url"],
            views=raw["metrics"]["views"],
            sales=raw["metrics"]["sales"],
            revenue_estimate=raw["metrics"]["revenue_estimate"],
            engagement_rate=raw["metrics"]["engagement_rate"],
            video_count=raw["metrics"]["video_count"],
            trend_status=raw["trend_status"],
            first_seen=datetime.fromisoformat(raw["first_seen"]),
            images=raw["images"],
            description=raw.get("description")
        )
```

**Этап 3: Хранение данных (1 день)**

Простая база данных для истории:

```python
# src/database/storage.py

import sqlite3
from datetime import datetime
from typing import List
import json

class ProductDatabase:
    """SQLite база для хранения продуктов и истории"""
    
    def __init__(self, db_path: str = "data/products.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Создание таблиц"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица продуктов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                name TEXT,
                price REAL,
                category TEXT,
                region TEXT,
                shop_url TEXT,
                first_seen TEXT,
                last_updated TEXT,
                images TEXT,
                description TEXT
            )
        ''')
        
        # Таблица метрик (история)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS metrics_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                date TEXT,
                views INTEGER,
                sales INTEGER,
                revenue_estimate REAL,
                engagement_rate REAL,
                video_count INTEGER,
                trend_status TEXT,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        ''')
        
        # Индексы для быстрого поиска
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_product_region 
            ON products(region)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_metrics_date 
            ON metrics_history(date)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_product(self, product: Product):
        """Сохранить продукт и его метрики"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Upsert продукта
        cursor.execute('''
            INSERT OR REPLACE INTO products 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product.id,
            product.name,
            product.price,
            product.category,
            product.region,
            product.shop_url,
            product.first_seen.isoformat(),
            datetime.now().isoformat(),
            json.dumps(product.images),
            product.description
        ))
        
        # Добавить метрики
        cursor.execute('''
            INSERT INTO metrics_history 
            (product_id, date, views, sales, revenue_estimate, 
             engagement_rate, video_count, trend_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product.id,
            datetime.now().date().isoformat(),
            product.views,
            product.sales,
            product.revenue_estimate,
            product.engagement_rate,
            product.video_count,
            product.trend_status
        ))
        
        conn.commit()
        conn.close()
    
    def get_trending_growth(self, days: int = 7) -> List[dict]:
        """Получить продукты с наибольшим ростом за период"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Сравниваем метрики начала и конца периода
        query = f'''
            WITH start_metrics AS (
                SELECT product_id, views as start_views, sales as start_sales
                FROM metrics_history
                WHERE date = date('now', '-{days} days')
            ),
            end_metrics AS (
                SELECT product_id, views as end_views, sales as end_sales
                FROM metrics_history
                WHERE date = date('now')
            )
            SELECT 
                p.id, p.name, p.price, p.category, p.region,
                s.start_views, e.end_views, 
                (e.end_views - s.start_views) as views_growth,
                s.start_sales, e.end_sales,
                (e.end_sales - s.start_sales) as sales_growth
            FROM products p
            JOIN start_metrics s ON p.id = s.product_id
            JOIN end_metrics e ON p.id = e.product_id
            ORDER BY views_growth DESC
        '''
        
        cursor.execute(query)
        results = cursor.fetchall()
        conn.close()
        
        return results
```

---

## 🤖 ИИ-Агент: Интеллектуальный анализ

### Архитектура агента

```
┌─────────────────────────────────────────────────────┐
│                 AI ANALYZER                          │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │   Module 1   │  │   Module 2   │  │ Module 3 │  │
│  │              │  │              │  │          │  │
│  │   Trend      │  │  Likato Fit  │  │   SSR    │  │
│  │  Detection   │  │   Analyzer   │  │  Testing │  │
│  │              │  │              │  │          │  │
│  └──────────────┘  └──────────────┘  └──────────┘  │
│         ↓                  ↓                 ↓      │
│  ┌──────────────────────────────────────────────┐  │
│  │         Ranking & Recommendation             │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### Module 1: Trend Detection (Детектор трендов)

**Задача:** Определить какие продукты действительно трендовые (не просто популярные)

```python
# src/ai_agent/trend_detector.py

from typing import List, Dict
import numpy as np
from sklearn.linear_model import LinearRegression

class TrendDetector:
    """Анализирует тренды и определяет стадию жизненного цикла"""
    
    def analyze_trends(self, products: List[Product]) -> List[Dict]:
        """
        Классификация продуктов по стадиям тренда:
        - 🚀 Early (ранняя стадия) - только начинает взлетать
        - 📈 Rising (растущий) - активный рост
        - 🔥 Peak (пик) - максимальная популярность
        - 📉 Declining (спад) - уже проходит
        """
        
        results = []
        
        for product in products:
            # Получаем историю метрик
            history = self.db.get_metrics_history(product.id, days=14)
            
            if len(history) < 3:
                continue  # недостаточно данных
            
            # Анализ динамики
            trend_data = self._analyze_growth_pattern(history)
            
            # Классификация стадии
            stage = self._classify_stage(trend_data)
            
            # Прогноз на следующую неделю
            forecast = self._forecast_next_week(history)
            
            results.append({
                "product": product,
                "stage": stage,
                "growth_rate": trend_data["growth_rate"],
                "acceleration": trend_data["acceleration"],
                "forecast_views": forecast["views"],
                "forecast_sales": forecast["sales"],
                "opportunity_score": self._calculate_opportunity_score(
                    stage, trend_data, forecast
                )
            })
        
        return results
    
    def _analyze_growth_pattern(self, history: List[dict]) -> dict:
        """Анализ паттерна роста"""
        
        dates = np.array([h["date"] for h in history])
        views = np.array([h["views"] for h in history])
        
        # Скорость роста (первая производная)
        growth_rate = np.gradient(views)
        
        # Ускорение (вторая производная)
        acceleration = np.gradient(growth_rate)
        
        # Средняя скорость роста за последние 7 дней
        avg_growth = np.mean(growth_rate[-7:])
        
        # Коэффициент вариации (стабильность роста)
        cv = np.std(growth_rate) / np.mean(growth_rate) if np.mean(growth_rate) > 0 else 0
        
        return {
            "growth_rate": avg_growth,
            "acceleration": np.mean(acceleration[-3:]),
            "stability": 1 / (1 + cv),  # 0-1, чем выше - тем стабильнее
            "total_growth": (views[-1] - views[0]) / views[0] if views[0] > 0 else 0
        }
    
    def _classify_stage(self, trend_data: dict) -> str:
        """Классификация стадии тренда"""
        
        growth_rate = trend_data["growth_rate"]
        acceleration = trend_data["acceleration"]
        
        if growth_rate > 100000 and acceleration > 0:
            return "early"  # 🚀 Ранняя стадия - быстрый рост с ускорением
        elif growth_rate > 50000 and acceleration >= 0:
            return "rising"  # 📈 Растущий - стабильный рост
        elif growth_rate > 0 and acceleration < 0:
            return "peak"  # 🔥 Пик - рост замедляется
        else:
            return "declining"  # 📉 Спад
    
    def _forecast_next_week(self, history: List[dict]) -> dict:
        """Простой прогноз на следующую неделю"""
        
        if len(history) < 7:
            return {"views": history[-1]["views"], "sales": history[-1]["sales"]}
        
        # Линейная регрессия для прогноза
        X = np.array(range(len(history))).reshape(-1, 1)
        y_views = np.array([h["views"] for h in history])
        y_sales = np.array([h["sales"] for h in history])
        
        model_views = LinearRegression().fit(X, y_views)
        model_sales = LinearRegression().fit(X, y_sales)
        
        next_week = len(history) + 7
        forecast_views = model_views.predict([[next_week]])[0]
        forecast_sales = model_sales.predict([[next_week]])[0]
        
        return {
            "views": max(0, int(forecast_views)),
            "sales": max(0, int(forecast_sales))
        }
    
    def _calculate_opportunity_score(
        self, stage: str, trend_data: dict, forecast: dict
    ) -> float:
        """
        Оценка перспективности для Likato (0-100)
        
        Высокий скор = выгодно производить аналог
        """
        
        score = 0
        
        # Бонус за стадию
        stage_bonus = {
            "early": 40,    # Лучшее время для входа
            "rising": 30,   # Хорошее время
            "peak": 10,     # Уже поздновато
            "declining": 0  # Не стоит
        }
        score += stage_bonus[stage]
        
        # Бонус за стабильность роста
        score += trend_data["stability"] * 20
        
        # Бонус за прогнозируемый объём продаж
        if forecast["sales"] > 10000:
            score += 20
        elif forecast["sales"] > 5000:
            score += 10
        
        # Бонус за скорость роста
        if trend_data["growth_rate"] > 100000:
            score += 20
        elif trend_data["growth_rate"] > 50000:
            score += 10
        
        return min(100, score)
```

### Module 2: Likato Fit Analyzer (Анализ соответствия Likato)

**Задача:** Оценить насколько продукт подходит для производства/продажи под брендом Likato

```python
# src/ai_agent/likato_fit_analyzer.py

from openai import OpenAI
from typing import Dict

class LikatoFitAnalyzer:
    """
    Анализирует насколько трендовый продукт подходит для Likato
    Использует GPT-4 для интеллектуального анализа
    """
    
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        
        # Контекст о Likato
        self.likato_context = """
        Likato - российский производитель натуральной косметики:
        - Специализация: спреи для волос, кремы для лица, молочко для тела
        - Популярные продукты: Magic Spray (10 в 1), спрей 17 в 1, кремы с ниацинамидом
        - Позиционирование: натуральные ингредиенты, multi-benefit продукты
        - Каналы продаж: likato.com, OZON (Россия), Amazon
        - Целевая аудитория: 25-45 лет, женщины, средний доход
        - Ценовой сегмент: средний (500-1500₽ / $15-50)
        - Производство: Cosmo Beauty Ltd (Россия)
        - Сильные стороны: быстрая разработка формул, natural positioning
        """
    
    def analyze_fit(self, product: Product, trend_data: dict) -> Dict:
        """
        Анализ соответствия продукта бренду Likato
        
        Возвращает:
        - fit_score: 0-100 (насколько подходит)
        - reasons: список причин почему подходит/не подходит
        - adaptations: как адаптировать под Likato
        - risks: потенциальные риски
        """
        
        # Получаем детали продукта
        product_details = self._get_product_context(product)
        
        # Промпт для GPT-4
        prompt = f"""
Ты - эксперт по разработке beauty продуктов. Проанализируй трендовый продукт и оцени насколько он подходит для производства под брендом Likato.

КОНТЕКСТ О LIKATO:
{self.likato_context}

ТРЕНДОВЫЙ ПРОДУКТ:
Название: {product.name}
Категория: {product.category}
Цена: ${product.price}
Описание: {product.description or 'нет описания'}

МЕТРИКИ ТРЕНДА:
- Просмотры: {product.views:,}
- Продажи (оценка): {product.sales:,}
- Выручка (оценка): ${product.revenue_estimate:,.0f}
- Стадия тренда: {trend_data['stage']}
- Прогноз продаж (неделя): {trend_data['forecast_sales']:,}

ВИДЕО С ПРОДУКТОМ (топ 3):
{product_details['top_videos']}

ЗАДАЧА:
1. Оцени FIT SCORE (0-100): насколько этот продукт подходит для Likato?
   - 80-100: Отлично подходит, нужно делать
   - 60-79: Хорошо подходит с небольшими адаптациями
   - 40-59: Частично подходит, требует серьезных изменений
   - 0-39: Не подходит

2. REASONS (причины): 3-5 пунктов почему подходит или не подходит
   Учитывай:
   - Соответствие категории (волосы/лицо/тело)
   - Соответствие позиционированию (натуральность, multi-benefit)
   - Ценовой сегмент
   - Сложность производства
   - Регуляторные риски (можно ли производить в РФ и продавать в US)

3. ADAPTATIONS (адаптации): как изменить/адаптировать продукт под Likato
   Например:
   - Добавить натуральные ингредиенты
   - Сделать multi-benefit версию
   - Упаковка в спрей формат
   - Изменить позиционирование

4. RISKS (риски): 2-3 основных риска
   - Производственные
   - Регуляторные
   - Конкурентные

Ответь СТРОГО в JSON формате:
{{
  "fit_score": 85,
  "reasons": [
    "Причина 1",
    "Причина 2"
  ],
  "adaptations": [
    "Адаптация 1",
    "Адаптация 2"
  ],
  "risks": [
    "Риск 1",
    "Риск 2"
  ],
  "recommendation": "Краткая рекомендация (1-2 предложения)"
}}
"""
        
        # Запрос к GPT-4
        response = self.client.chat.completions.create(
            model="gpt-4o",  # или gpt-4-turbo
            messages=[
                {"role": "system", "content": "Ты эксперт по beauty продуктам и product development. Отвечаешь только в JSON формате."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # низкая температура для более консистентных оценок
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return result
    
    def _get_product_context(self, product: Product) -> dict:
        """Получить дополнительный контекст о продукте"""
        
        # Получаем топ видео с продуктом из PiPiAds
        details = pipiads_client.get_product_details(product.id)
        
        top_videos = []
        for video in details.get("videos", [])[:3]:
            top_videos.append(
                f"- @{video['creator']}: {video['views']:,} просмотров, "
                f"{video['likes']:,} лайков"
            )
        
        return {
            "top_videos": "\n".join(top_videos) if top_videos else "нет данных"
        }
```

### Module 3: SSR Testing (Симуляция покупателей)

**Задача:** Протестировать концепт продукта на "виртуальных покупателях" через SSR метод

```python
# src/ai_agent/ssr_tester.py

from openai import OpenAI
import numpy as np
from typing import List, Dict

class SSRTester:
    """
    Semantic Similarity Rating для тестирования концептов
    На основе метода из исследования arXiv:2510.08338
    """
    
    def __init__(self, openai_api_key: str):
        self.client = OpenAI(api_key=openai_api_key)
        
        # Эталонные фразы для шкалы Лайкерта (1-5)
        self.reference_phrases = {
            1: "Определённо не куплю этот продукт. Он мне совсем не подходит.",
            2: "Скорее всего не куплю. Есть сомнения и он не вызывает интереса.",
            3: "Нейтрально отношусь. Может быть куплю, если будет скидка.",
            4: "Скорее всего куплю. Продукт интересный и подходит мне.",
            5: "Определённо куплю! Именно то, что мне нужно."
        }
        
        # Персоны целевой аудитории Likato
        self.personas = [
            {
                "name": "Анна",
                "age": 28,
                "profile": "Женщина 28 лет, средний доход, интересуется натуральной косметикой, активный пользователь OZON, следит за трендами в beauty"
            },
            {
                "name": "Мария",
                "age": 35,
                "profile": "Женщина 35 лет, доход выше среднего, предпочитает качественные продукты, заботится о составе, покупает на Amazon"
            },
            {
                "name": "Елена",
                "age": 42,
                "profile": "Женщина 42 лет, средний доход, ищет эффективные решения для волос/кожи, ценит multi-benefit продукты"
            }
        ]
    
    def test_concept(self, product_name: str, description: str, price: float) -> Dict:
        """
        Тестирование концепта продукта на виртуальных покупателях
        
        Возвращает:
        - average_rating: средняя оценка (1-5)
        - purchase_intent: % вероятность покупки
        - persona_feedback: отзывы от каждой персоны
        """
        
        results = []
        
        for persona in self.personas:
            # Шаг 1: Получаем текстовый ответ от LLM (от лица персоны)
            text_response = self._get_persona_response(
                persona, product_name, description, price
            )
            
            # Шаг 2: Конвертируем текст в числовую оценку через SSR
            rating_distribution = self._text_to_rating(text_response)
            
            # Шаг 3: Вычисляем ожидаемое значение
            expected_rating = sum(
                rating * prob for rating, prob in rating_distribution.items()
            )
            
            results.append({
                "persona": persona["name"],
                "text_response": text_response,
                "rating": expected_rating,
                "distribution": rating_distribution
            })
        
        # Агрегированные результаты
        avg_rating = np.mean([r["rating"] for r in results])
        purchase_intent = sum(1 for r in results if r["rating"] >= 4) / len(results) * 100
        
        return {
            "average_rating": round(avg_rating, 2),
            "purchase_intent_pct": round(purchase_intent, 1),
            "persona_feedback": results,
            "recommendation": self._interpret_results(avg_rating, purchase_intent)
        }
    
    def _get_persona_response(
        self, persona: dict, product_name: str, description: str, price: float
    ) -> str:
        """Получить текстовый ответ от персоны"""
        
        prompt = f"""
Ты - {persona['profile']}.

Тебе показали новый beauty продукт:
Название: {product_name}
Описание: {description}
Цена: {price}₽

Насколько вероятно, что ты купишь этот продукт? 
Ответь естественным языком (2-3 предложения), как бы ответил реальный человек.
Объясни своё решение: что нравится, что смущает, купишь ли ты.
"""
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",  # быстрая модель для персон
            messages=[
                {"role": "system", "content": f"Ты играешь роль: {persona['profile']}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8  # высокая температура для разнообразия ответов
        )
        
        return response.choices[0].message.content
    
    def _text_to_rating(self, text_response: str) -> Dict[int, float]:
        """
        Конвертация текста в распределение оценок через SSR
        
        Метод:
        1. Получаем embeddings текста ответа
        2. Получаем embeddings эталонных фраз (1-5)
        3. Вычисляем косинусное сходство
        4. Нормализуем в вероятностное распределение
        """
        
        # Получаем embedding ответа
        response_embedding = self._get_embedding(text_response)
        
        # Получаем embeddings эталонных фраз
        similarities = {}
        for rating, phrase in self.reference_phrases.items():
            phrase_embedding = self._get_embedding(phrase)
            similarity = self._cosine_similarity(response_embedding, phrase_embedding)
            similarities[rating] = similarity
        
        # Нормализуем в вероятностное распределение (softmax)
        total = sum(np.exp(s) for s in similarities.values())
        distribution = {
            rating: np.exp(sim) / total 
            for rating, sim in similarities.items()
        }
        
        return distribution
    
    def _get_embedding(self, text: str) -> np.ndarray:
        """Получить embedding текста"""
        response = self.client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return np.array(response.data[0].embedding)
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Косинусное сходство"""
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
    
    def _interpret_results(self, avg_rating: float, purchase_intent: float) -> str:
        """Интерпретация результатов"""
        if avg_rating >= 4.0 and purchase_intent >= 70:
            return "🟢 Отличный концепт! Высокий интерес целевой аудитории."
        elif avg_rating >= 3.5 and purchase_intent >= 50:
            return "🟡 Хороший концепт. Требует небольших доработок для усиления интереса."
        elif avg_rating >= 3.0:
            return "🟠 Средний интерес. Нужны значительные улучшения концепта."
        else:
            return "🔴 Низкий интерес. Концепт не подходит для целевой аудитории."
```

### Объединение всех модулей: Ranking & Recommendation

```python
# src/ai_agent/orchestrator.py

from typing import List, Dict
import pandas as pd

class AIOrchestrator:
    """
    Главный оркестратор ИИ-агента
    Объединяет все модули и выдаёт финальные рекомендации
    """
    
    def __init__(
        self, 
        trend_detector: TrendDetector,
        likato_analyzer: LikatoFitAnalyzer,
        ssr_tester: SSRTester
    ):
        self.trend_detector = trend_detector
        self.likato_analyzer = likato_analyzer
        self.ssr_tester = ssr_tester
    
    def analyze_weekly_opportunities(
        self, products: List[Product]
    ) -> Dict:
        """
        Еженедельный анализ всех трендовых продуктов
        
        Возвращает топ-10 лучших возможностей для Likato
        """
        
        results = []
        
        print(f"🔍 Анализирую {len(products)} трендовых продуктов...")
        
        for i, product in enumerate(products, 1):
            print(f"  [{i}/{len(products)}] {product.name}")
            
            # 1. Анализ тренда
            trend_analysis = self.trend_detector.analyze_trends([product])[0]
            
            # Фильтр: только early/rising стадии
            if trend_analysis["stage"] in ["declining", "peak"]:
                continue
            
            # 2. Анализ соответствия Likato
            fit_analysis = self.likato_analyzer.analyze_fit(
                product, trend_analysis
            )
            
            # Фильтр: fit_score >= 60
            if fit_analysis["fit_score"] < 60:
                continue
            
            # 3. SSR тестирование (опционально, для топ кандидатов)
            # Пропускаем для MVP, чтобы не тратить много API запросов
            # Можно включить для финального топ-10
            
            # Вычисляем общий скор
            overall_score = self._calculate_overall_score(
                trend_analysis, fit_analysis
            )
            
            results.append({
                "product": product,
                "overall_score": overall_score,
                "trend_analysis": trend_analysis,
                "fit_analysis": fit_analysis,
                "ssr_results": None  # пока отключено
            })
        
        # Сортируем по общему скору
        results.sort(key=lambda x: x["overall_score"], reverse=True)
        
        # Топ-10
        top_opportunities = results[:10]
        
        # Для топ-3 делаем SSR тестирование
        print("\n🧪 SSR тестирование топ-3 кандидатов...")
        for i, opp in enumerate(top_opportunities[:3]):
            product = opp["product"]
            
            # Формируем концепт продукта для Likato
            concept = self._create_likato_concept(
                product, opp["fit_analysis"]["adaptations"]
            )
            
            # Тестируем
            ssr_results = self.ssr_tester.test_concept(
                concept["name"],
                concept["description"],
                concept["price"]
            )
            
            opp["ssr_results"] = ssr_results
            opp["overall_score"] += ssr_results["average_rating"] * 5  # бонус за SSR
        
        # Пересортируем с учётом SSR
        top_opportunities.sort(key=lambda x: x["overall_score"], reverse=True)
        
        return {
            "total_analyzed": len(products),
            "qualified_opportunities": len(results),
            "top_10": top_opportunities,
            "summary": self._generate_summary(top_opportunities)
        }
    
    def _calculate_overall_score(
        self, trend_analysis: dict, fit_analysis: dict
    ) -> float:
        """
        Вычисление общего скора возможности
        
        Формула:
        overall_score = opportunity_score * 0.4 + fit_score * 0.6
        
        fit_score важнее, т.к. тренд без соответствия бренду бесполезен
        """
        return (
            trend_analysis["opportunity_score"] * 0.4 +
            fit_analysis["fit_score"] * 0.6
        )
    
    def _create_likato_concept(
        self, product: Product, adaptations: List[str]
    ) -> dict:
        """Создать концепт продукта для Likato на основе тренда"""
        
        # Берём оригинальный продукт и адаптируем под Likato
        concept_name = f"Likato {product.category} - вдохновлён {product.name}"
        
        concept_description = f"""
Натуральный {product.category.lower()} на основе трендового продукта.
Адаптации для Likato:
{chr(10).join(f'- {a}' for a in adaptations)}
"""
        
        # Цена в рублях (примерно)
        concept_price = product.price * 90 * 1.2  # USD to RUB + наценка
        
        return {
            "name": concept_name,
            "description": concept_description,
            "price": concept_price
        }
    
    def _generate_summary(self, top_opportunities: List[dict]) -> str:
        """Генерация саммари для отчёта"""
        
        summary = f"""
📊 ЕЖЕНЕДЕЛЬНЫЙ ОТЧЁТ PRODUCTRADA

Найдено топ-{len(top_opportunities)} возможностей для Likato.

🥇 ТОП-3 ПРИОРИТЕТНЫХ:

"""
        for i, opp in enumerate(top_opportunities[:3], 1):
            product = opp["product"]
            fit = opp["fit_analysis"]
            trend = opp["trend_analysis"]
            
            summary += f"""
{i}. {product.name}
   Общий скор: {opp['overall_score']:.1f}/100
   Стадия тренда: {trend['stage']} ({trend['opportunity_score']:.0f}/100)
   Соответствие Likato: {fit['fit_score']}/100
   Рекомендация: {fit['recommendation']}
"""
            
            if opp["ssr_results"]:
                ssr = opp["ssr_results"]
                summary += f"""   SSR тест: {ssr['average_rating']:.1f}/5 ⭐, {ssr['purchase_intent_pct']:.0f}% намерены купить
   {ssr['recommendation']}
"""
        
        return summary
```

---

## 🗓️ План разработки MVP (поэтапно)

### **Неделя 1: Фундамент** (5 дней)

#### День 1: Настройка инфраструктуры
- ✅ Регистрация PiPiAds (Pro план $199/мес)
- ✅ Получение API ключа
- ✅ Настройка OpenAI API
- ✅ Создание структуры проекта
```
product-radar/
├── src/
│   ├── data_collector/
│   │   └── pipiads_client.py
│   ├── database/
│   │   └── storage.py
│   ├── ai_agent/
│   │   ├── trend_detector.py
│   │   ├── likato_fit_analyzer.py
│   │   └── ssr_tester.py
│   └── orchestrator/
│       └── main.py
├── data/
│   └── products.db
├── config/
│   └── config.yaml
├── reports/
└── tests/
```

#### День 2-3: Data Pipeline
- ✅ Реализация `PiPiAdsClient`
- ✅ Тестирование API запросов
- ✅ Реализация `ProductDatabase`
- ✅ Первый сбор данных (US, Beauty категория)
- ✅ Валидация качества данных

#### День 4: Module 1 - Trend Detector
- ✅ Реализация `TrendDetector`
- ✅ Анализ динамики роста
- ✅ Классификация стадий тренда
- ✅ Тестирование на реальных данных

#### День 5: Интеграция и тестирование
- ✅ Объединение Data Pipeline + Trend Detector
- ✅ Первый автоматический сбор и анализ
- ✅ Исправление багов
- ✅ Документация

**Результат недели 1:** Работающий сбор данных + базовый анализ трендов

---

### **Неделя 2: ИИ-анализ** (5 дней)

#### День 6-7: Module 2 - Likato Fit Analyzer
- ✅ Реализация `LikatoFitAnalyzer`
- ✅ Промпт-инжиниринг для GPT-4
- ✅ Тестирование на 10-20 продуктах
- ✅ Калибровка оценок (fit_score)

#### День 8-9: Module 3 - SSR Tester
- ✅ Реализация `SSRTester`
- ✅ Создание персон целевой аудитории
- ✅ Реализация SSR метода
- ✅ Тестирование на концептах

#### День 10: Orchestrator
- ✅ Реализация `AIOrchestrator`
- ✅ Объединение всех модулей
- ✅ Формула overall_score
- ✅ End-to-end тест

**Результат недели 2:** Полный ИИ-агент, способный анализировать и ранжировать возможности

---

### **Неделя 3: Автоматизация и отчёты** (5 дней)

#### День 11-12: Weekly Pipeline
- ✅ Автоматический запуск раз в неделю
- ✅ Обработка ошибок и retry логика
- ✅ Логирование
- ✅ Мониторинг

```python
# src/scheduler/weekly_job.py

import schedule
import time
from datetime import datetime

def weekly_analysis_job():
    """Еженедельная задача анализа"""
    
    print(f"\n{'='*60}")
    print(f"🚀 Запуск еженедельного анализа: {datetime.now()}")
    print(f"{'='*60}\n")
    
    try:
        # 1. Сбор данных из PiPiAds
        print("📥 Шаг 1/4: Сбор данных из PiPiAds...")
        pipiads = PiPiAdsClient(api_key=CONFIG["pipiads_api_key"])
        
        regions = ["US", "TH", "VN"]  # США + Азия
        all_products = []
        
        for region in regions:
            products = pipiads.get_trending_products(
                region=region,
                category="Beauty & Personal Care",
                time_range="7d",
                limit=50
            )
            all_products.extend(products)
            print(f"  ✓ {region}: {len(products)} продуктов")
        
        # 2. Сохранение в БД
        print(f"\n💾 Шаг 2/4: Сохранение в базу данных...")
        db = ProductDatabase()
        for product in all_products:
            db.save_product(product)
        print(f"  ✓ Сохранено: {len(all_products)} продуктов")
        
        # 3. ИИ-анализ
        print(f"\n🤖 Шаг 3/4: ИИ-анализ...")
        orchestrator = AIOrchestrator(
            trend_detector=TrendDetector(),
            likato_analyzer=LikatoFitAnalyzer(CONFIG["openai_api_key"]),
            ssr_tester=SSRTester(CONFIG["openai_api_key"])
        )
        
        results = orchestrator.analyze_weekly_opportunities(all_products)
        
        # 4. Генерация отчёта
        print(f"\n📊 Шаг 4/4: Генерация отчёта...")
        report = generate_weekly_report(results)
        
        # Сохранение отчёта
        report_path = f"reports/week_{datetime.now().strftime('%Y_%W')}.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"  ✓ Отчёт сохранён: {report_path}")
        
        # Отправка email (опционально)
        if CONFIG.get("send_email"):
            send_email_report(report)
            print(f"  ✓ Email отправлен")
        
        print(f"\n{'='*60}")
        print(f"✅ Анализ завершён успешно!")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        # Отправить алерт
        send_alert_email(f"Weekly job failed: {e}")

# Запуск каждый понедельник в 10:00
schedule.every().monday.at("10:00").do(weekly_analysis_job)

print("📅 Scheduler запущен. Ожидание еженедельных задач...")
while True:
    schedule.run_pending()
    time.sleep(3600)  # проверка каждый час
```

#### День 13: Report Generator
- ✅ Форматирование отчёта (Markdown + HTML)
- ✅ Визуализации (графики трендов)
- ✅ Email рассылка

```python
# src/reports/generator.py

def generate_weekly_report(results: dict) -> str:
    """Генерация красивого отчёта"""
    
    report = f"""
# 📊 ProductRadar Weekly Report
**Дата:** {datetime.now().strftime('%Y-%m-%d')}  
**Период:** последние 7 дней

---

## 🎯 Executive Summary

{results['summary']}

---

## 📈 Детальный анализ топ-10

"""
    
    for i, opp in enumerate(results['top_10'], 1):
        product = opp['product']
        trend = opp['trend_analysis']
        fit = opp['fit_analysis']
        ssr = opp.get('ssr_results')
        
        report += f"""
### {i}. {product.name}

**Общий скор:** {opp['overall_score']:.1f}/100  
**Категория:** {product.category}  
**Цена:** ${product.price}  
**Регион:** {product.region}

**📊 Метрики тренда:**
- Просмотры: {product.views:,}
- Продажи (оценка): {product.sales:,}
- Выручка (оценка): ${product.revenue_estimate:,.0f}
- Количество видео: {product.video_count}
- Стадия: {trend['stage']} (скор {trend['opportunity_score']:.0f}/100)
- Прогноз продаж (+7 дней): {trend['forecast_sales']:,}

**🎨 Соответствие Likato: {fit['fit_score']}/100**

*Почему подходит:*
{chr(10).join(f'- {r}' for r in fit['reasons'])}

*Как адаптировать:*
{chr(10).join(f'- {a}' for a in fit['adaptations'])}

*Риски:*
{chr(10).join(f'- ⚠️ {r}' for r in fit['risks'])}

**💡 Рекомендация:** {fit['recommendation']}
"""
        
        if ssr:
            report += f"""
**🧪 SSR тестирование:**
- Средняя оценка: {ssr['average_rating']:.1f}/5 ⭐
- Намерение купить: {ssr['purchase_intent_pct']:.0f}%
- {ssr['recommendation']}

*Отзывы виртуальных покупателей:*
{chr(10).join(f'- **{p["persona"]}** ({p["rating"]:.1f}/5): "{p["text_response"]}"' for p in ssr['persona_feedback'])}
"""
        
        report += f"\n🔗 [Посмотреть на TikTok Shop]({product.shop_url})\n\n---\n"
    
    report += f"""
## 📌 Статистика

- Всего проанализировано продуктов: {results['total_analyzed']}
- Прошли фильтры (early/rising + fit≥60): {results['qualified_opportunities']}
- Выбрано в топ-10: {len(results['top_10'])}

---

*Отчёт сгенерирован автоматически ProductRadar AI Agent*
"""
    
    return report
```

#### День 14-15: Dashboard (опционально)
- ✅ Простой веб-интерфейс (Streamlit)
- ✅ Просмотр истории отчётов
- ✅ Интерактивные графики
- ✅ Ручной запуск анализа

```python
# src/dashboard/app.py

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="ProductRadar Dashboard", layout="wide")

st.title("📊 ProductRadar AI Dashboard")

# Sidebar
st.sidebar.header("Настройки")
week = st.sidebar.selectbox("Выбрать неделю", get_available_weeks())

# Кнопка запуска анализа
if st.sidebar.button("🚀 Запустить анализ сейчас"):
    with st.spinner("Анализ может занять 5-10 минут..."):
        weekly_analysis_job()
    st.success("Анализ завершён!")

# Основной контент
tab1, tab2, tab3 = st.tabs(["📈 Топ возможности", "📊 Аналитика", "⚙️ История"])

with tab1:
    st.header("Топ-10 возможностей этой недели")
    
    # Загрузить результаты
    results = load_weekly_results(week)
    
    for i, opp in enumerate(results['top_10'], 1):
        with st.expander(f"{i}. {opp['product'].name} - Скор: {opp['overall_score']:.1f}/100"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.image(opp['product'].images[0])
                st.metric("Просмотры", f"{opp['product'].views:,}")
                st.metric("Продажи (оценка)", f"{opp['product'].sales:,}")
            
            with col2:
                st.metric("Стадия тренда", opp['trend_analysis']['stage'])
                st.metric("Fit Score", f"{opp['fit_analysis']['fit_score']}/100")
                if opp.get('ssr_results'):
                    st.metric("SSR Rating", f"{opp['ssr_results']['average_rating']:.1f}/5")
            
            st.write("**Рекомендация:**", opp['fit_analysis']['recommendation'])

with tab2:
    st.header("Аналитика трендов")
    
    # График динамики топ продуктов
    df = get_metrics_history(results['top_10'])
    fig = px.line(df, x='date', y='views', color='product_name', 
                  title='Динамика просмотров топ-10 продуктов')
    st.plotly_chart(fig, use_container_width=True)
    
    # Распределение по категориям
    category_dist = get_category_distribution(results['top_10'])
    fig2 = px.pie(values=category_dist.values(), names=category_dist.keys(),
                  title='Распределение по категориям')
    st.plotly_chart(fig2)

with tab3:
    st.header("История отчётов")
    
    reports = get_all_reports()
    for report in reports:
        with st.expander(f"Неделя {report['week']} - {report['date']}"):
            st.markdown(report['content'])
```

**Результат недели 3:** Полностью автоматизированная система с еженедельными отчётами

---

## 💰 Оценка стоимости MVP

### Разработка (единоразово)
- **3 недели работы** - уже в зарплате программиста
- **Итого:** 0₽ дополнительных затрат на разработку

### Инфраструктура (ежемесячно)

**Обязательные:**
- **PiPiAds Pro:** $199/мес = ~18,000₽
- **OpenAI API:** ~$50-100/мес = ~4,500-9,000₽
  - GPT-4o для анализа: ~50 продуктов × 2 запроса × $0.01 = ~$1
  - GPT-4o-mini для SSR: ~10 концептов × 3 персоны × $0.001 = ~$0.03
  - Embeddings: ~100 запросов × $0.0001 = ~$0.01
  - **Итого за неделю:** ~$1-2
  - **За месяц (4 недели):** ~$4-8
  - **С запасом:** $50-100/мес
- **Сервер:** VPS для автозапуска = ~1,000₽/мес (или свой = 0₽)

**Опциональные:**
- **Email сервис:** SendGrid (бесплатно до 100 писем/день)
- **Dashboard хостинг:** Streamlit Cloud (бесплатно) или VPS

**ИТОГО в месяц:** 23,500-28,000₽ (~$260-310)

**ИТОГО в год:** 282,000-336,000₽

### Сравнение с альтернативами

| Вариант | Год 1 | Год 2+ | Качество анализа |
|---------|-------|--------|------------------|
| **Наш MVP (PiPiAds + AI)** | 282-336k₽ | 282-336k₽ | ⭐⭐⭐⭐⭐ Умный |
| Только PiPiAds (без AI) | 216-324k₽ | 216-324k₽ | ⭐⭐⭐ Сырые данные |
| Свой парсер + AI | 150-400k₽ | 100-300k₽ | ⭐⭐⭐⭐ Нестабильно |
| Гибрид (свой парсер со 2-го года) | 282-336k₽ | 150-300k₽ | ⭐⭐⭐⭐⭐ |

**Рекомендация:** Начать с PiPiAds + AI (наш MVP), оценить ROI за 3-6 месяцев, потом решить нужен ли свой парсер.

---

## 🎯 Roadmap после MVP

### Квартал 2: Улучшения (месяц 2-4)

**Месяц 2: Дополнительные источники**
- Интеграция Instagram Reels (через Apify)
- Интеграция Amazon Best Sellers
- Кросс-платформенный анализ трендов

**Месяц 3: Улучшение AI**
- Fine-tuning GPT для лучших оценок fit_score
- Расширение персон для SSR (5-7 персон)
- A/B тестирование промптов
- Добавление sentiment analysis отзывов

**Месяц 4: Автоматизация действий**
- Автоматическое создание карточек товаров для OZON
- Генерация креативов/идей для маркетинга
- Интеграция с CRM для отслеживания R&D пайплайна

### Квартал 3-4: Масштабирование (месяц 5-12)

**Расширение регионов:**
- Европа (UK, DE, FR)
- Латинская Америка (MX, BR)
- Ближний Восток (UAE)

**Расширение категорий:**
- Home & Living (для диверсификации)
- Wellness & Health

**Собственный парсер (опционально):**
- Разработка своего парсера параллельно
- Переход на гибридную модель
- Экономия ~100-200k₽/год со 2-го года

**ML модели:**
- Предсказание успеха продукта (ML classifier)
- Оптимизация цены
- Персонализация рекомендаций

---

## ✅ Чеклист запуска MVP

### Неделя 1
- [ ] Зарегистрироваться на PiPiAds, купить Pro ($199/мес)
- [ ] Получить API ключ PiPiAds
- [ ] Настроить OpenAI API
- [ ] Создать структуру проекта
- [ ] Реализовать `PiPiAdsClient`
- [ ] Реализовать `ProductDatabase`
- [ ] Первый тестовый сбор данных
- [ ] Реализовать `TrendDetector`
- [ ] Протестировать анализ трендов

### Неделя 2
- [ ] Реализовать `LikatoFitAnalyzer`
- [ ] Протестировать GPT-4 анализ на 10-20 продуктах
- [ ] Калибровать оценки fit_score
- [ ] Реализовать `SSRTester`
- [ ] Протестировать SSR на концептах
- [ ] Реализовать `AIOrchestrator`
- [ ] End-to-end тест всей системы

### Неделя 3
- [ ] Настроить автоматический запуск (scheduler)
- [ ] Реализовать Report Generator
- [ ] Настроить email рассылку
- [ ] Создать Dashboard (опционально)
- [ ] Финальное тестирование
- [ ] Документация
- [ ] **Запуск в продакшн!**

---

## 📞 Что дальше?

### Следующие шаги:

1. **Утвердить роудмап** - согласовать с командой
2. **Купить PiPiAds** - начать с trial (7 дней бесплатно)
3. **Протестировать API** - убедиться что данные подходят
4. **Начать разработку** - неделя 1

### Вопросы для обсуждения:

1. ✅ **Регионы Азии:** Точно Thailand + Vietnam? Или добавить другие?
2. ✅ **Частота отчётов:** Weekly достаточно или нужен daily мониторинг?
3. ✅ **Dashboard:** Нужен или хватит email отчётов?
4. ✅ **Бюджет:** Готовы тратить ~$260-310/мес на инфраструктуру?
5. ✅ **Персоны для SSR:** 3 персоны достаточно или расширить?

---

**Готов начинать разработку?** 🚀

