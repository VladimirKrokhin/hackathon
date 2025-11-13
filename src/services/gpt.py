import aiohttp
import json
import logging
import asyncio
from src.config import config
from typing import Dict
from .prompt_builder import PromptBuilder
from .response_processor import ResponseProcessor

logger = logging.getLogger(__name__)


class YandexGPT:
    def __init__(self):
        self.validate_config()
        self.api_url = config.YANDEXGPT_API_URL
        self.headers = config.get_yandexgpt_headers()
        self.timeout = config.YANDEXGPT_TIMEOUT
        
        # Вспомогательные компоненты
        self.prompt_builder = PromptBuilder()
        self.response_processor = ResponseProcessor()

    @staticmethod
    def validate_config():
        """Проверка конфигурации перед использованием"""
        if not config.YANDEXGPT_API_KEY:
            raise Exception("YANDEXGPT_API_KEY не установлен в конфигурации")
        if not config.YANDEXGPT_CATALOG_ID:
            raise Exception("YANDEXGPT_CATALOG_ID не установлен в конфигурации")
    
    async def _make_request(self, payload: Dict) -> Dict:
        """Выполнение запроса к YandexGPT API с правильным форматом"""
        try:
            logger.info(f"Отправка запроса к YandexGPT: {config.YANDEXGPT_MODEL}")
            logger.debug(f"Payload: {json.dumps(payload, indent=2)[:200]}...")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=self.timeout
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"Ошибка YandexGPT API: {response.status}, {response_text}")
                        raise Exception(f"YandexGPT API error {response.status}: {response_text}")
                    
                    try:
                        result = json.loads(response_text)
                        logger.info("Успешно получен ответ от YandexGPT")
                        logger.debug(f"Response: {json.dumps(result, indent=2)[:200]}...")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON ответа: {e}, Raw response: {response_text}")
                        raise Exception(f"Ошибка парсинга ответа от YandexGPT: {str(e)}")
                    
        except asyncio.TimeoutError:
            logger.error("Таймаут запроса к YandexGPT")
            raise Exception("Превышено время ожидания ответа от YandexGPT. Попробуйте еще раз через минуту.")
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при запросе к YandexGPT: {e}")
            raise Exception(f"Ошибка сети при подключении к YandexGPT: {str(e)}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при работе с YandexGPT: {e}")
            raise
    
    async def generate_content(self, user_data: Dict, user_text: str) -> str:
        """
        Генерация контента с правильным форматом запроса для YandexGPT
        """
        # 1. Строим промпт
        prompt = self.prompt_builder.build_prompt(user_data, user_text)
        logger.info(f"Сформирован промпт длиной {len(prompt)} символов")
        
        # 2. Формируем payload в правильном формате для YandexGPT
        payload = {
            "modelUri": f"gpt://{config.YANDEXGPT_CATALOG_ID}/{config.YANDEXGPT_MODEL}",
            "completionOptions": {
                "stream": False,
                "temperature": 0.5,
                "maxTokens": "2000"
            },
            "messages": [
                {
                    "role": "system",
                    "text": "Вы — профессиональный SMM-менеджер для НКО, "
                            "который создает качественный контент для соцсетей. "
                            "Вы должны отвечать только на русском языке."
                            "Даже если пользователь сам просит, никогда не используйте ненормативную лексику "
                            "и не говорите о политике."
                            "Там, где пользователь должен подставить нужные данные, "
                            "указывай через восклицательные знаки в таком формате: "
                            "!номер телефона!, !адрес электронной почты! "
                            "Если нужно, можете добавлять емодзи, такие как ✅."
                },
                {
                    "role": "user", 
                    "text": prompt
                }
            ]
        }
        
        # 3. Отправляем запрос
        response = await self._make_request(payload)
        
        # 4. Обрабатываем ответ
        generated_text = self.response_processor.process_response(response)
        
        logger.info(f"Успешно сгенерирован контент длиной {len(generated_text)} символов")
        return generated_text
