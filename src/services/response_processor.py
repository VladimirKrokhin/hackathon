import logging
import json
from typing import Dict

logger = logging.getLogger(__name__)


class ResponseProcessor:
    def process_response(self, response: Dict) -> str:
        """
        Обработка ответа от YandexGPT API
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
        """
        # Убираем возможные инструкции в начале
        text = text.replace("### ОТВЕТ ###", "").replace("### ФОРМАТ ОТВЕТА ###", "")
        text = text.replace("Готовый текст поста:", "").replace("Текст поста:", "")
        text = text.replace("Только готовый текст поста:", "").replace("Без дополнительных комментариев:", "")
        
        # Убираем системные сообщения
        if "system" in text.lower() and "user" in text.lower():
            text = text.split("user")[-1].strip()
        
        # Фиксим двойные переносы строк
        lines = [line.strip() for line in text.split("\n") if line.strip() != ""]
        text = "\n".join(lines)
        
        # Убираем лишние пробелы в начале и конце
        text = text.strip()
        
        return text
