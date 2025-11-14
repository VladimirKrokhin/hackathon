import asyncio
import json
import logging
from abc import ABC, ABCMeta, abstractmethod
from typing import Dict

import aiohttp

from config import config

logger = logging.getLogger(__name__)


class AbstractGPT(ABC):
    """Базовый интерфейс для моделей GPT."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Возвращает имя модели."""
        pass

    @abstractmethod
    async def generate(self, prompt: str) -> Dict:
        """Возвращает сырой ответ модели по промпту."""


class ApiGPT(AbstractGPT, metaclass=ABCMeta):
    """Абстрактный класс для GPT, работающих через HTTP API."""

    def __init__(
        self,
        *,
        api_url: str,
        headers: Dict[str, str],
        timeout: int,
    ):
        self.api_url = api_url
        self.headers = headers
        self.timeout = timeout


    @abstractmethod
    def build_payload(self, prompt: str, system_prompt: str) -> Dict:
        """Собирает payload для конкретного запроса."""
        pass

    async def generate(self, prompt: str, system_prompt) -> Dict:
        payload = self.build_payload(prompt, system_prompt)
        response = await self._make_request(payload)
        logger.info("Сырой ответ от модели получен")
        return response

    async def _make_request(self, payload: Dict) -> Dict:
        """Универсальный запрос к GPT API."""
        try:
            logger.info(f"Отправка запроса к {self.model_name}")
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
                        logger.error(f"Ошибка API {self.model_name}: {response.status}, {response_text}")
                        raise Exception(f"{self.model_name} API error {response.status}: {response_text}")
                    
                    try:
                        result = json.loads(response_text)
                        logger.info(f"Успешно получен ответ от {self.model_name}")
                        logger.debug(f"Ответ: {json.dumps(result, indent=2)[:200]}...")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON ответа: {e}, Сырой запрос: {response_text}")
                        raise Exception(f"Ошибка парсинга ответа от {self.model_name}: {str(e)}")
                    
        except asyncio.TimeoutError:
            logger.error(f"Таймаут запроса к {self.model_name}")
            raise Exception(f"Превышено время ожидания ответа от {self.model_name}. Попробуйте еще раз через минуту.")
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при запросе к {self.model_name}: {e}")
            raise Exception(f"Ошибка сети при подключении к {self.model_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при работе с {self.model_name}: {e}")
            raise

def get_yandexgpt_headers(api_key) -> Dict[str, str]:
    """Заголовки для YandexGPT API"""
    return {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}",
    }

class YandexGPT(ApiGPT):

    def __init__(self):
        super().__init__(
            api_url=config.YANDEXGPT_API_URL,
            headers=get_yandexgpt_headers(config.YANDEXGPT_API_KEY),
            timeout=config.YANDEXGPT_TIMEOUT,
        )

    @property
    def model_name(self) -> str:
        return f"YandexGPT ({config.YANDEXGPT_MODEL})"


    def build_payload(self, prompt: str, system_prompt: str) -> Dict:
        return {
            "modelUri": f"gpt://{config.YANDEXGPT_CATALOG_ID}/{config.YANDEXGPT_MODEL}",
            "completionOptions": {
                "stream": False,
                "temperature": config.YANDEXGPT_TEMPERATURE,
                "maxTokens": str(config.YANDEXGPT_MAX_TOKENS),
            },
            "messages": [
                {
                    "role": "system",
                    "text": system_prompt,
                },
                {
                    "role": "user",
                    "text": prompt
                }
            ]
        }
