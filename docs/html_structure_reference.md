# Справочник HTML структуры для парсинга

## 📍 Страница товара (TikTok Ads блок)

### Структура одной карточки видео

Основной контейнер: `<div class="item-inner is-tk">`

---

### 1️⃣ IMPRESSION (на карточке)

**Местоположение:**
```html
<div class="data-count">
    <div class="item">
        <p class="value"> 33 </p>
        <p class="caption"> Impression </p>
    </div>
</div>
```

**Селектор для парсинга:**
- Контейнер: `div.data-count`
- Ищем блок с `caption` = "Impression"
- Значение в `p.value`

**Примеры значений:**
- `33` (минимальное)
- `720`
- `748.2K`
- `1.2M`
- `4.1M`

---

### 2️⃣ FIRST SEEN (на карточке)

**Местоположение:**
```html
<div class="other-info flex flex-wrap">
    <div class="flex ellipsis-one-line align-center time-line-wrap">
        <div class="el-tooltip create-time btn item">
            <svg>...</svg>
            <span> Nov 05 2025-Nov 11 2025 </span>
        </div>
    </div>
</div>
```

**Селектор для парсинга:**
- Контейнер: `div.create-time` или `div.time-line-wrap`
- Значение в `<span>` внутри `.create-time`
- Формат: "Nov 05 2025-Nov 11 2025" (диапазон дат)

**Примеры значений:**
- `Nov 05 2025-Nov 11 2025` (7 дней)
- `Oct 18 2025-Nov 14 2025` (28 дней)
- `Jan 31 2025-Aug 11 2025` (>30 дней)

**ВАЖНО:** Нам нужна **первая дата** (first_seen) из диапазона!

---

### 3️⃣ AD-SEARCH ССЫЛКА (на карточке)

**Местоположение:**
```html
<div class="btn-wraps flex flex-shrink-0">
    <a href="/ad-search/639a2a46eccb3746d443/" 
       class="el-tooltip btn-detail" 
       target="_blank">
        <svg>...</svg>
    </a>
</div>
```

**Селектор для парсинга:**
- `a.btn-detail[href*="/ad-search/"]`
- Значение в атрибуте `href`

**Примеры:**
- `/ad-search/639a2a46eccb3746d443/`
- `/ad-search/4d151909d67658db7ba0/`

---

## 📍 Страница ad-search

### 4️⃣ IMPRESSION (на странице ad-search)

**Местоположение:**
```html
<div class="addel-board-item">
    <div class="value"> 726.9K </div>
    <div class="name"> Impression </div>
</div>
```

**Селектор:**
- Ищем `div.addel-board-item` где `div.name` содержит "Impression"
- Значение в `div.value`

---

### 5️⃣ FIRST SEEN (на странице ad-search)

**Местоположение:**
```html
<div class="addel-info-item">
    <div class="name"> First seen - Last seen </div>
    <div class="value"> Oct 29 2025 ~ Nov 13 2025 </div>
</div>
```

**Селектор:**
- Ищем `div.addel-info-item` где `div.name` содержит "First seen"
- Значение в `div.value`
- Формат: "Oct 29 2025 ~ Nov 13 2025"

**ВАЖНО:** Нам нужна **первая дата** (до `~`)!

---

### 6️⃣ AUDIENCE (на странице ad-search)

**Местоположение:**
```html
<div class="addel-info-item">
    <div class="name"> Audience </div>
    <div class="value">
        <div class="audience-info">
            <div class="audience-info-info">
                <span class="icon-user">...</span>
                45-55
                <i class="line"></i>
                &nbsp; Android
            </div>
        </div>
    </div>
</div>
```

**Селектор:**
- Ищем `div.addel-info-item` где `div.name` = "Audience"
- Значение в `div.audience-info-info` (текстовый контент)
- Формат: "45-55" (возрастной диапазон)

**ВАЖНО:** Извлекаем только возраст, игнорируем "Android" и иконки!

---

### 7️⃣ COUNTRY (на странице ad-search)

**Местоположение:**
```html
<div class="addel-info-item">
    <div class="name"> Country/Region </div>
    <div class="value ellipsis-box">
        <div class="ellipsis"> Philippines </div>
        <span>(1)</span>
    </div>
</div>
```

**Селектор:**
- Ищем `div.addel-info-item` где `div.name` = "Country/Region"
- Значение в `div.ellipsis`

---

### 8️⃣ SCRIPT (на странице ad-search)

**Местоположение:**
```html
<li id="ai-script">
    <div class="li-title">
        <svg>...</svg>
        <span class="tit-text">Script</span>
    </div>
    <div class="control-content li-content">
        <p class="content-text slot-wrap">
            Ang iyong mga panloob na hita din ito madilim? ...
        </p>
    </div>
</li>
```

**Селектор:**
- `li#ai-script p.content-text`
- Извлекаем текст (может быть длинным)

---

### 9️⃣ HOOK (на странице ad-search)

**Местоположение:**
```html
<li id="ai-hook">
    <div class="li-title">
        <svg>...</svg>
        <span class="tit-text">Hooks</span>
    </div>
    <div class="control-content li-content">
        <p class="content-text slot-wrap">
            Ang iyong mga panloob na hita din ito madilim?
        </p>
    </div>
</li>
```

**Селектор:**
- `li#ai-hook p.content-text`
- Извлекаем текст

---

## 🔍 Важные замечания

### Количество карточек
- Скрипт находит **117 карточек**, но пользователь видит только **36**
- Возможно, карточки подгружаются динамически при скролле
- **Решение**: Работать с теми карточками, которые уже загружены (36)

### Приоритет данных
1. **На странице товара** (быстрее, не требует переходов):
   - Impression
   - First seen
   - Ad-search ссылка

2. **На странице ad-search** (требует перехода):
   - Script
   - Hook
   - Audience
   - Country
   - Более точные Impression и First seen (если нужно)

### Форматы дат
- **На карточке:** `Nov 05 2025-Nov 11 2025` (диапазон через дефис)
- **На ad-search:** `Oct 29 2025 ~ Nov 13 2025` (диапазон через тильду)

### Критерии фильтрации
**ГЛОБАЛЬНАЯ ЛОГИКА:** Скрипт запускается в первый день недели для проверки результатов за прошлую неделю (последние 7 дней).

- **Минимум impression:** 1K (1000)
- **Возраст видео:** СТРОГО не старше 7 дней от сегодняшней даты
  - Видео старше 7 дней - НЕ БРАТЬ
- **Выбор видео:** Топ-3 видео по просмотрам (impression) из всех подходящих

