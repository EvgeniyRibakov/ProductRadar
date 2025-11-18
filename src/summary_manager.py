"""
Управление саммари итераций
"""

from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import re

SUMMARIES_DIR = Path("logs/summaries")

def get_latest_summaries(count: int = 10) -> List[Path]:
    """Получить список последних саммари"""
    if not SUMMARIES_DIR.exists():
        return []
    
    files = sorted(
        SUMMARIES_DIR.glob("iteration_*.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    return files[:count]

def parse_summary_info(file_path: Path) -> Dict[str, str]:
    """Извлечь основную информацию из саммари"""
    try:
        content = file_path.read_text(encoding="utf-8")
        
        # Извлекаем дату из имени файла
        match = re.search(r"iteration_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})", file_path.name)
        timestamp = match.group(1) if match else ""
        
        # Парсим основную информацию
        successful = re.search(r"\*\*Успешно обработано:\*\* (\d+)", content)
        skipped = re.search(r"\*\*Пропущено:\*\* (\d+)", content)
        checked = re.search(r"\*\*Проверено:\*\* (\d+)", content)
        
        # Определяем статус
        status = "❌"
        if "ЦЕЛЬ ДОСТИГНУТА" in content:
            status = "✅"
        elif "Достигнут лимит" in content:
            status = "⚠️"
        
        return {
            "file": file_path.name,
            "timestamp": timestamp,
            "status": status,
            "successful": successful.group(1) if successful else "0",
            "skipped": skipped.group(1) if skipped else "0",
            "checked": checked.group(1) if checked else "0",
        }
    except Exception:
        return {
            "file": file_path.name,
            "timestamp": "",
            "status": "❓",
            "successful": "?",
            "skipped": "?",
            "checked": "?",
        }

def read_summary(file_path: Path) -> str:
    """Прочитать содержимое саммари"""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"❌ Ошибка при чтении файла: {e}"

def create_summary_extract(content: str) -> str:
    """Создать краткую выжимку из саммари"""
    lines = content.split("\n")
    extract = []
    
    # Заголовок
    for line in lines[:3]:
        if line.startswith("# 📊"):
            extract.append(line)
            break
    
    # Результаты (только цифры)
    extract.append("\n## ✅ Результаты\n")
    for line in lines:
        if "## ✅ Результаты" in line:
            continue
        elif line.startswith("- **Успешно"):
            extract.append(line)
        elif line.startswith("- **Пропущено"):
            extract.append(line)
        elif line.startswith("- **Проверено"):
            extract.append(line)
        elif line.startswith("##") and "Результаты" not in line:
            break
    
    # Только успешные товары (максимум 3, только название и топ-1 видео)
    extract.append("\n### ✅ Успешно обработанные товары:\n")
    
    in_product = False
    current_product_name = ""
    products_count = 0
    found_first_video = False
    
    for line in lines:
        if "### ✅ Товар #" in line:
            if products_count >= 3:  # Максимум 3 товара
                break
            if current_product_name:
                extract.append("")  # Пустая строка между товарами
            # Извлекаем название товара
            product_name = line.split(": ", 1)[-1] if ": " in line else line.split("### ✅ Товар #")[-1]
            if len(product_name) > 60:
                product_name = product_name[:57] + "..."
            extract.append(f"**{product_name}**")
            current_product_name = product_name
            in_product = True
            products_count += 1
            found_first_video = False
        elif in_product:
            if line.startswith("1. ✅ **") and "impressions" in line and not found_first_video:
                # Только первое (лучшее) видео
                impression_match = re.search(r"\*\*([^*]+)\s+impressions\*\*", line)
                first_seen_match = re.search(r"First seen:\s+([^\n]+)", line)
                impression = impression_match.group(1) if impression_match else ""
                first_seen = first_seen_match.group(1).strip() if first_seen_match else ""
                extract.append(f"   🥇 {impression} impressions | {first_seen}")
                found_first_video = True
            elif line.startswith("---") or (line.startswith("###") and "Товар" not in line and "Успешно" not in line):
                in_product = False
                current_product_name = ""
    
    # Статус
    for line in lines:
        if "## 🎯 Статус:" in line:
            extract.append("\n" + line)
            break
    
    return "\n".join(extract)

def format_summary_list(summaries: List[Path]) -> str:
    """Форматировать список саммари для Telegram"""
    if not summaries:
        return "📊 Саммари не найдены"
    
    lines = ["📊 Последние итерации:\n"]
    
    for idx, summary_path in enumerate(summaries, 1):
        info = parse_summary_info(summary_path)
        
        # Форматируем дату
        date_str = info["timestamp"]
        if date_str:
            try:
                dt = datetime.strptime(date_str, "%Y-%m-%d_%H-%M-%S")
                date_str = dt.strftime("%d.%m.%Y %H:%M")
            except:
                pass
        
        lines.append(
            f"{idx}. {info['status']} {date_str} - "
            f"Успешно: {info['successful']}, "
            f"Проверено: {info['checked']}"
        )
    
    return "\n".join(lines)

def split_message(text: str, max_length: int = 4096) -> List[str]:
    """Разбить длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current = ""
    
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_length:
            if current:
                parts.append(current)
                current = ""
        
        if len(line) > max_length:
            # Слишком длинная строка - разбиваем по словам
            words = line.split(" ")
            for word in words:
                if len(current) + len(word) + 1 > max_length:
                    if current:
                        parts.append(current)
                        current = ""
                current += word + " " if current else word
        else:
            current += line + "\n" if current else line + "\n"
    
    if current:
        parts.append(current)
    
    return parts

