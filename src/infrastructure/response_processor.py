from abc import ABC, abstractmethod
import json
import re
from typing import Dict


import logging

logger = logging.getLogger(__name__)

class AbstractResponseProcessor(ABC):
    @abstractmethod
    def process_response(self, response: Dict) -> str:
        """
        Обработка ответа от GPT
        """
        pass

class YandexGPTResponseProcessor(AbstractResponseProcessor):
    def process_response(self, response: Dict) -> str:
        """
        Обработка ответа от GPT
        """
        try:
            # Извлекаем текст из ответа
            if "result" in response and "alternatives" in response["result"]:
                alternative = response["result"]["alternatives"][0]
                if "message" in alternative and "text" in alternative["message"]:
                    generated_text = alternative["message"]["text"].strip()
                    logger.info(f"Извлечен текст из ответа: {generated_text[:200]}...")
                    
                    # Минимальная постобработка
                    processed_text = self._minimal_post_process(generated_text)
                    return processed_text
            
            # Если не смогли извлечь текст
            error_msg = f"Не удалось извлечь текст из ответа YandexGPT: {json.dumps(response)}"
            logger.error(error_msg)
            raise Exception("Не удалось извлечь сгенерированный текст из ответа YandexGPT")
            
        except KeyError as e:
            logger.error(f"Ошибка при извлечении данных из ответа: {e}")
            raise Exception(f"Ошибка формата ответа от YandexGPT: {str(e)}")
        except Exception as e:
            logger.error(f"Ошибка при обработке ответа: {e}")
            raise

    @staticmethod
    def _minimal_post_process(text: str) -> str:
        """
        Минимальная постобработка текста:
        - Убираем лишние инструкции
        - Фиксим форматирование
        - Удаляем восклицательные знаки вокруг реальных данных (телефонов, email и т.д.)
        """
        # Убираем возможные инструкции в начале
        text = text.replace("### ОТВЕТ ###", "").replace("### ФОРМАТ ОТВЕТА ###", "")
        text = text.replace("Готовый текст поста:", "").replace("Текст поста:", "")
        text = text.replace("Только готовый текст поста:", "").replace("Без дополнительных комментариев:", "")
        
        # Убираем системные сообщения
        if "system" in text.lower() and "user" in text.lower():
            text = text.split("user")[-1].strip()
        
        # Удаляем восклицательные знаки вокруг реальных данных
        text = YandexGPTResponseProcessor._remove_exclamation_marks_around_data(text)
        
        # Фиксим двойные переносы строк
        lines = [line.strip() for line in text.split("\n") if line.strip() != ""]
        text = "\n".join(lines)
        
        # Убираем лишние пробелы в начале и конце
        text = text.strip()
        
        return text

    @staticmethod
    def _remove_exclamation_marks_around_data(text: str) -> str:
        """
        Удаляет восклицательные знаки вокруг реальных данных:
        - Телефоны (форматы: +7..., 8..., (xxx) xxx-xx-xx и т.д.)
        - Email адреса
        - URL адреса
        - Другие реальные данные, которые не являются шаблонами
        
        ВАЖНО: Обрабатывает только полные паттерны !...! (с двумя восклицательными знаками).
        Шаблоны (содержащие слова типа "номер телефона", "адрес электронной почты") сохраняются.
        """
        # Ключевые слова, которые указывают на шаблон (не реальные данные)
        template_keywords = [
            'номер', 'телефон', 'адрес', 'электронной', 'почты', 'email', 
            'контакт', 'телефона', 'почта', 'email-адрес', 'email адрес'
        ]
        
        def process_exclamation_pattern(match):
            """
            Обрабатывает паттерн !...! и решает, нужно ли убирать восклицательные знаки.
            """
            content = match.group(1).strip()
            content_lower = content.lower()
            
            # Если содержит ключевые слова шаблона - это шаблон, оставляем как есть
            if any(keyword in content_lower for keyword in template_keywords):
                return match.group(0)  # Возвращаем !...! без изменений
            
            # Проверяем, является ли содержимое реальными данными
            # Телефон: содержит только цифры, пробелы, дефисы, скобки, плюс
            if re.match(r'^[+]?[0-9\s\-\(\)]{7,20}$', content):
                return content  # Убираем восклицательные знаки
            
            # Email: содержит @ и точку
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', content):
                return content  # Убираем восклицательные знаки
            
            # URL: начинается с http:// или https://
            if re.match(r'^https?://[^\s!]+$', content):
                return content  # Убираем восклицательные знаки
            
            # Адрес: содержит ключевые слова адреса
            if re.search(r'(ул\.|улица|д\.|дом|кв\.|квартира|г\.|город)', content_lower):
                return content  # Убираем восклицательные знаки
            
            # Если содержит цифры или специальные символы (@, /, :), но не является шаблоном
            # и не является явно реальными данными - оставляем как есть (на всякий случай)
            # Это может быть что-то неопределенное, лучше не трогать
            return match.group(0)
        
        # Обрабатываем только полные паттерны !...! (с двумя восклицательными знаками)
        # Это гарантирует, что мы не трогаем одиночные восклицательные знаки
        text = re.sub(r'!([^!]+)!', process_exclamation_pattern, text)
        
        return text


