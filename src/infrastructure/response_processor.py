"""
Инфраструктура обработки ответов от GPT моделей.

Данный модуль предоставляет интерфейсы и реализации для обработки ответов
от различных GPT API. Извлекает и пост-обрабатывает сгенерированный текстовый
контент из ответов API, обрабатывая форматирование и очистку данных.
"""

from abc import ABC, abstractmethod
import json
import re
from typing import Dict

import logging

# Настройка логирования для модуля
logger = logging.getLogger(__name__)


class AbstractResponseProcessor(ABC):
    """
    Абстрактный базовый класс для обработки ответов GPT API.
    
    Определяет интерфейс для всех процессоров ответов, которые обрабатывают
    извлечение и пост-обработку сгенерированного текста из различных
    ответов GPT.
    """
    
    @abstractmethod
    def process_response(self, response: Dict) -> str:
        """
        Обрабатывает сырой ответ GPT и извлекает сгенерированный текст.
        
        Args:
            response (Dict): Сырой ответ от GPT API
            
        Returns:
            str: Обработанный и очищенный текстовый контент
            
        Raises:
            Exception: При неудаче извлечения текста
        """
        pass


class YandexGPTResponseProcessor(AbstractResponseProcessor):
    """
    Процессор ответов для YandexGPT API.
    
    Обрабатывает извлечение сгенерированного текста из ответов YandexGPT API
    и выполняет пост-обработку для очистки и форматирования контента.
    """
    
    def process_response(self, response: Dict) -> str:
        """
        Обрабатывает ответ YandexGPT API и извлекает сгенерированный текст.
        
        Извлекает текст из структуры ответа YandexGPT и применяет
        минимальную пост-обработку, включая очистку формата и
        валидацию данных.
        
        Args:
            response (Dict): Сырой ответ от YandexGPT API
            
        Returns:
            str: Обработанный и очищенный сгенерированный текст
            
        Raises:
            Exception: При неудаче извлечения текста или некорректном формате ответа
        """
        try:
            # Извлекаем текст из структуры ответа
            if "result" in response and "alternatives" in response["result"]:
                alternative = response["result"]["alternatives"][0]
                if "message" in alternative and "text" in alternative["message"]:
                    generated_text = alternative["message"]["text"].strip()
                    logger.info(f"Извлечен текст из ответа: {generated_text[:200]}...")
                    
                    # Применяем минимальную пост-обработку
                    processed_text = self._minimal_post_process(generated_text)
                    return processed_text
            
            # Если извлечение текста не удалось
            error_msg = f"Не удалось извлечь текст из ответа YandexGPT: {json.dumps(response)}"
            logger.error(error_msg)
            raise Exception("Не удалось извлечь сгенерированный текст из ответа YandexGPT")
            
        except KeyError as e:
            logger.error(f"Ошибка при извлечении данных из ответа: {e}")
            raise Exception(f"Ошибка формата ответа YandexGPT: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа: {e}")
            raise

    @staticmethod
    def _minimal_post_process(text: str) -> str:
        """
        Выполняет минимальную пост-обработку сгенерированного текста.
        
        Применяет базовые операции очистки, включая:
        - Удаление заголовков инструкций
        - Исправление проблем форматирования
        - Удаление восклицательных знаков вокруг реальных данных (телефоны, email и т.д.)
        - Удаление лишних пробелов
        
        Args:
            text (str): Сырой сгенерированный текст
            
        Returns:
            str: Очищенный и обработанный текст
        """
        # Удаляем возможные заголовки инструкций
        text = text.replace("### ОТВЕТ ###", "").replace("### ФОРМАТ ОТВЕТА ###", "")
        text = text.replace("Готовый текст поста:", "").replace("Текст поста:", "")
        text = text.replace("Только готовый текст поста:", "").replace("Без дополнительных комментариев:", "")
        
        # Удаляем системные сообщения
        if "system" in text.lower() and "user" in text.lower():
            text = text.split("user")[-1].strip()
        
        # Удаляем восклицательные знаки вокруг реальных данных
        text = YandexGPTResponseProcessor._remove_exclamation_marks_around_data(text)
        
        # Удаляем лишние пробелы в начале и конце
        text = text.strip()
        
        return text

    @staticmethod
    def _remove_exclamation_marks_around_data(text: str) -> str:
        """
        Удаляет восклицательные знаки вокруг реальных данных, сохраняя шаблоны.
        
        Обрабатывает паттерны типа !...! (с двумя восклицательными знаками) и удаляет
        их, если содержимое является реальными данными (номера телефонов, email, адреса).
        Сохраняет восклицательные знаки для шаблонов (контент с ключевыми словами типа
        "номер телефона", "адрес электронной почты" и т.д.).
        
        Args:
            text (str): Текст с потенциальными паттернами восклицательных знаков
            
        Returns:
            str: Текст с удаленными восклицательными знаками вокруг реальных данных
        """
        # Ключевые слова, указывающие на шаблон (не реальные данные)
        template_keywords = [
            'номер', 'телефон', 'адрес', 'электронной', 'почты', 'email', 
            'контакт', 'телефона', 'почта', 'email-адрес', 'email адрес'
        ]
        
        def process_exclamation_pattern(match):
            """
            Обрабатывает паттерн !...! и определяет, нужно ли удалять восклицательные знаки.
            
            Args:
                match: Объект regex match, содержащий паттерн
                
            Returns:
                str: Содержимое с или без восклицательных знаков
            """
            content = match.group(1).strip()
            content_lower = content.lower()
            
            # Если содержит ключевые слова шаблона - это шаблон, оставляем как есть
            if any(keyword in content_lower for keyword in template_keywords):
                return match.group(0)  # Возвращаем !...! без изменений
            
            # Проверяем, является ли содержимое реальными данными
            # Телефон: содержит только цифры, пробелы, дефисы, скобки, плюс
            if re.match(r'^[+]?[0-9\s\-\(\)]{7,20}$', content):
                return content  # Удаляем восклицательные знаки
            
            # Email: содержит @ и точку
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', content):
                return content  # Удаляем восклицательные знаки
            
            # URL: начинается с http:// или https://
            if re.match(r'^https?://[^\s!]+$', content):
                return content  # Удаляем восклицательные знаки
            
            # Адрес: содержит ключевые слова адресов
            if re.search(r'(ул\.|улица|д\.|дом|кв\.|квартира|г\.|город)', content_lower):
                return content  # Удаляем восклицательные знаки
            
            # Если содержит числа или специальные символы, но не является явно реальными данными
            # Оставляем как есть для безопасности
            return match.group(0)
        
        # Обрабатываем только полные паттерны !...! (с двумя восклицательными знаками)
        # Это гарантирует, что мы не трогаем одиночные восклицательные знаки
        text = re.sub(r'!([^!]+)!', process_exclamation_pattern, text)
        
        return text
