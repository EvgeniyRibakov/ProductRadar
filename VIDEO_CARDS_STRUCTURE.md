# Структура карточек видео на странице товара Pipiads

## Общая структура

Все карточки видео находятся внутри блока:
```html
<ul class="lists-wrap wt-block-grid wt-list-unstyled wt-block-grid-xs-1 wt-block-grid-sm-1 wt-block-grid-md-2 wt-block-grid-lg-3 wt-block-grid-xl-4">
  <li class="item-wrap wt-block-grid__item">
    <!-- Карточка видео -->
  </li>
</ul>
```

**Селектор для поиска всех карточек:**
```css
ul.lists-wrap li.item-wrap.wt-block-grid__item
```
или
```css
li.item-wrap.wt-block-grid__item
```

---

## Структура одной карточки видео

### Полная структура карточки:
```html
<li class="item-wrap wt-block-grid__item">
  <div class="item-inner is-tk">
    <!-- Обложка видео -->
    <div class="cover-container">...</div>
    
    <!-- Нижняя часть с данными -->
    <div class="bottom-wrap">
      <!-- Блок с датой -->
      <div class="other-info flex flex-wrap">
        <div class="flex ellipsis-one-line align-center time-line-wrap">
          <div class="el-tooltip create-time btn item">
            <svg>...</svg>
            <span>Nov 09 2025-Nov 15 2025</span>  <!-- FIRST_SEEN -->
          </div>
        </div>
      </div>
      
      <!-- Блок с метриками (impression, дни, лайки) -->
      <div class="data-count">
        <div class="item">
          <p class="value">38.2K</p>  <!-- IMPRESSION -->
          <p class="caption">Впечатление</p>
        </div>
        <div class="item">
          <p class="value">3</p>
          <p class="caption">Дни</p>
        </div>
        <div class="item">
          <p class="value">161</p>
          <p class="caption">Нравится</p>
        </div>
      </div>
      
      <!-- Кнопка с ссылкой на ad-search -->
      <div class="btn-wraps flex flex-shrink-0">
        <a href="/ad-search/baf95a8cdc7ba3d43c6e/" class="el-tooltip btn-detail" target="_blank">
          <!-- AD_SEARCH_URL -->
        </a>
      </div>
    </div>
  </div>
</li>
```

---

## Извлечение данных

### 1. IMPRESSION (Впечатление)

**Расположение:**
```html
<div class="data-count">
  <div class="item">
    <p class="value">38.2K</p>  <!-- ЗДЕСЬ -->
    <p class="caption">Впечатление</p>  <!-- Идентификатор -->
  </div>
</div>
```

**Селекторы для извлечения:**
```css
/* Вариант 1: По структуре (рекомендуется) */
div.data-count div.item

/* Вариант 2: Прямой селектор */
div.data-count div.item p.value

/* Вариант 3: По caption */
div.data-count div.item:has(p.caption:contains("Впечатление")) p.value
```

**Алгоритм извлечения:**
1. Найти все `div.data-count div.item`
2. Для каждого элемента найти `p.caption`
3. Проверить текст caption на наличие "Впечатление" или "Impression"
4. Если совпадает, взять значение из `p.value` того же `div.item`

**Примеры значений:**
- `16.2K` → 16200
- `38.2K` → 38200
- `30.9K` → 30900
- `182.9K` → 182900
- `11.9M` → 11900000
- `1M` → 1000000
- `400.1K` → 400100

---

### 2. FIRST_SEEN (Дата первого просмотра)

**Расположение:**
```html
<div class="other-info flex flex-wrap">
  <div class="flex ellipsis-one-line align-center time-line-wrap">
    <div class="el-tooltip create-time btn item">
      <svg>...</svg>
      <span>Nov 09 2025-Nov 15 2025</span>  <!-- ЗДЕСЬ -->
    </div>
  </div>
</div>
```

**Селектор для извлечения:**
```css
div.create-time span
```

**Формат данных:**
- Полный формат: `Nov 09 2025-Nov 15 2025` (диапазон дат)
- Нужно извлечь: `Nov 09 2025` (первая дата до дефиса)

**Алгоритм извлечения:**
1. Найти `div.create-time span`
2. Извлечь текст
3. Использовать regex: `([A-Z][a-z]{2}\s+\d{1,2}\s+\d{4})` для извлечения первой даты
4. Результат: `Nov 09 2025`

**Примеры:**
- `Nov 10 2025-Nov 15 2025` → `Nov 10 2025`
- `Nov 09 2025-Nov 15 2025` → `Nov 09 2025`
- `Nov 07 2025-Nov 15 2025` → `Nov 07 2025`
- `Nov 04 2025-Nov 15 2025` → `Nov 04 2025`

---

### 3. AD_SEARCH_URL (Ссылка на страницу ad-search)

**Расположение:**
```html
<div class="btn-wraps flex flex-shrink-0">
  <a href="/ad-search/baf95a8cdc7ba3d43c6e/" class="el-tooltip btn-detail" target="_blank">
    <svg>...</svg>
  </a>
</div>
```

**Селектор для извлечения:**
```css
a.btn-detail[href*="/ad-search/"]
```

**Алгоритм извлечения:**
1. Найти `a.btn-detail[href*="/ad-search/"]`
2. Извлечь атрибут `href`
3. Нормализовать URL (добавить домен, убрать параметры, исправить опечатки)

**Примеры:**
- `/ad-search/baf95a8cdc7ba3d43c6e/` → `https://www.pipiads.com/ad-search/baf95a8cdc7ba3d43c6e`
- `/ad-search/62e2e1a3f6afc033d683/` → `https://www.pipiads.com/ad-search/62e2e1a3f6afc033d683`
- `/ad-search/92e8e20e53337dcf4acc/` → `https://www.pipiads.com/ad-search/92e8e20e53337dcf4acc`

**Важно:** Могут быть опечатки в URL:
- `/ad-seearch/...` → исправить на `/ad-search/...`

---

## Закономерности для всех карточек

### Общие характеристики:

1. **Все карточки имеют одинаковую структуру** - различаются только значениями
2. **Карточки находятся в `<ul>` с классом `lists-wrap`**
3. **Каждая карточка - это `<li>` с классом `item-wrap wt-block-grid__item`**
4. **Внутри карточки всегда есть:**
   - `div.data-count` - блок с метриками (impression, дни, лайки)
   - `div.create-time` - блок с датой
   - `a.btn-detail` - ссылка на ad-search

### Порядок элементов в карточке:

```
<li.item-wrap>
  └─ <div.item-inner>
      ├─ <div.cover-container> (обложка видео)
      └─ <div.bottom-wrap>
          ├─ <div.other-info>
          │   └─ <div.create-time> ← FIRST_SEEN
          ├─ <div.data-count> ← IMPRESSION
          │   └─ <div.item> (может быть несколько)
          │       ├─ <p.value> ← значение
          │       └─ <p.caption> ← название метрики
          └─ <div.btn-wraps>
              └─ <a.btn-detail> ← AD_SEARCH_URL
```

---

## Текущая реализация в коде

### Файл: `src/parser_engine.py`

**Функция:** `_extract_video_data_from_card()`

**Текущие селекторы:**
- **Impression:** `div.data-count div.item` → проверка `p.caption` → извлечение `p.value`
- **First_seen:** `div.create-time span` → regex для первой даты
- **Ad_search_url:** `a.btn-detail[href*="/ad-search/"]` → атрибут `href`

**Проблема:** Скрипт может смотреть только на первое видео и если оно не подходит, пропускает товар.

**Решение:** Нужно собирать данные ВСЕХ карточек на странице, а не только первой.

---

## Рекомендации для исправления

1. **Собирать все карточки:**
   ```python
   cards = await page.query_selector_all('li.item-wrap.wt-block-grid__item')
   ```

2. **Обрабатывать каждую карточку:**
   ```python
   for card in cards:
       video_data = await _extract_video_data_from_card(card)
   ```

3. **Фильтровать после сбора всех данных:**
   - Собрать все видео
   - Применить фильтры (impression >= 1000, first_seen <= 60 дней)
   - Выбрать топ-3

4. **Не останавливаться на первом неподходящем видео:**
   - Продолжать сбор данных даже если первое видео не подходит
   - Фильтрация должна происходить ПОСЛЕ сбора всех данных

---

## Примеры карточек из HTML

### Карточка 1:
- Impression: `16.2K`
- First_seen: `Nov 10 2025` (из `Nov 10 2025-Nov 15 2025`)
- Ad_search_url: `/ad-search/fd56711214418a5f37c3/`

### Карточка 2:
- Impression: `38.2K`
- First_seen: `Nov 09 2025` (из `Nov 09 2025-Nov 15 2025`)
- Ad_search_url: `/ad-search/baf95a8cdc7ba3d43c6e/`

### Карточка 3:
- Impression: `30.9K`
- First_seen: `Nov 07 2025` (из `Nov 07 2025-Nov 15 2025`)
- Ad_search_url: `/ad-search/62e2e1a3f6afc033d683/`

### Карточка 4:
- Impression: `182.9K`
- First_seen: `Nov 09 2025` (из `Nov 09 2025-Nov 15 2025`)
- Ad_search_url: `/ad-search/92e8e20e53337dcf4acc/`

### Карточка 5:
- Impression: `11.9M`
- First_seen: `Nov 04 2025` (из `Nov 04 2025-Nov 15 2025`)
- Ad_search_url: `/ad-search/37218d63072633d87b02/`

---

## Важные замечания

1. **Дата может быть в формате диапазона:** `Nov 09 2025-Nov 15 2025`
   - Всегда брать ПЕРВУЮ дату (до дефиса)
   - Это дата первого просмотра (first_seen)

2. **Impression может быть в разных форматах:**
   - `16.2K` = 16200
   - `1M` = 1000000
   - `11.9M` = 11900000
   - Нужен парсер для преобразования

3. **Ad_search_url может быть относительным:**
   - `/ad-search/...` → нужно добавить домен
   - Могут быть опечатки: `/ad-seearch/` → исправить

4. **Карточки могут загружаться динамически:**
   - Нужно прокручивать страницу для загрузки всех карточек
   - Может быть пагинация

---

## Дата создания документа

2025-11-15

## Последнее обновление

2025-11-15

