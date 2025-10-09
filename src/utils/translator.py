"""Утилиты для перевода текста"""

from typing import Optional
import asyncio
from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from src.config.settings import settings
from src.utils.logger import setup_logger


logger = setup_logger(__name__)


class Translator:
    """Класс для перевода текстов с использованием AI"""
    
    def __init__(self, use_openai: bool = True):
        """
        Инициализация переводчика
        
        Args:
            use_openai: Использовать OpenAI (иначе Anthropic)
        """
        self.use_openai = use_openai
        
        if use_openai and settings.openai_api_key:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            self.model = "gpt-3.5-turbo"
        elif settings.anthropic_api_key:
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.model = "claude-3-haiku-20240307"
        else:
            logger.warning("API ключи не найдены, перевод будет недоступен")
            self.client = None
    
    async def translate_chinese_to_russian(
        self, 
        text: str,
        context: Optional[str] = None
    ) -> str:
        """
        Перевод с китайского на русский
        
        Args:
            text: Текст для перевода
            context: Контекст (например: "название продукта", "хук")
            
        Returns:
            Переведенный текст
        """
        if not self.client:
            logger.warning("Клиент AI недоступен, возвращаем оригинальный текст")
            return text
        
        if not text or not text.strip():
            return text
        
        try:
            prompt = self._create_translation_prompt(text, context)
            
            if self.use_openai:
                return await self._translate_with_openai(prompt)
            else:
                return await self._translate_with_anthropic(prompt)
                
        except Exception as e:
            logger.error(f"Ошибка при переводе: {e}")
            return text
    
    def _create_translation_prompt(
        self, 
        text: str, 
        context: Optional[str]
    ) -> str:
        """Создание промпта для перевода"""
        base_prompt = f"Переведи следующий текст с китайского на русский язык: {text}"
        
        if context:
            if context == "название продукта":
                base_prompt += "\n\nЭто название косметического продукта. Переведи естественно, как его бы назвали в России."
            elif context == "хук":
                base_prompt += "\n\nЭто рекламный хук (3-7 слов). Адаптируй под русскоязычную аудиторию, сохраняя эмоциональный посыл."
            elif context == "оффер":
                base_prompt += "\n\nЭто торговое предложение. Переведи понятно для российского покупателя."
        
        base_prompt += "\n\nВерни ТОЛЬКО перевод, без объяснений."
        
        return base_prompt
    
    async def _translate_with_openai(self, prompt: str) -> str:
        """Перевод с использованием OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Ты профессиональный переводчик китайского языка, специализирующийся на косметике и бьюти-продуктах."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Ошибка OpenAI: {e}")
            raise
    
    async def _translate_with_anthropic(self, prompt: str) -> str:
        """Перевод с использованием Anthropic"""
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=200,
                system="Ты профессиональный переводчик китайского языка, специализирующийся на косметике и бьюти-продуктах.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Ошибка Anthropic: {e}")
            raise
    
    async def translate_product_fields(
        self, 
        product_data: dict
    ) -> dict:
        """
        Перевод всех необходимых полей продукта
        
        Args:
            product_data: Словарь с данными продукта
            
        Returns:
            Обновленный словарь с переводами
        """
        fields_to_translate = {
            'product_name_original': ('product_name_translated', 'название продукта'),
            'top_hooks_original': ('top_hooks_translated', 'хук'),
            'top_offers_original': ('top_offers_translated', 'оффер'),
            'why_works_original': ('why_works_translated', 'описание'),
        }
        
        for original_field, (translated_field, context) in fields_to_translate.items():
            if original_field in product_data and product_data[original_field]:
                original_text = product_data[original_field]
                translated_text = await self.translate_chinese_to_russian(
                    original_text, 
                    context
                )
                product_data[translated_field] = translated_text
        
        return product_data
    
    async def batch_translate(
        self, 
        texts: list[str], 
        context: Optional[str] = None
    ) -> list[str]:
        """
        Пакетный перевод текстов
        
        Args:
            texts: Список текстов для перевода
            context: Контекст перевода
            
        Returns:
            Список переведенных текстов
        """
        tasks = [
            self.translate_chinese_to_russian(text, context) 
            for text in texts
        ]
        
        return await asyncio.gather(*tasks)

