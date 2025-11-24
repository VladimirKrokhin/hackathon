"""
Модуль работы с GPT API.

Данный модуль предоставляет интерфейсы и реализации для работы с различными 
моделями генерации текста через HTTP API. Поддерживает абстракции для 
создания клиентов и обработки запросов к GPT-сервисам.

Основные компоненты:
- AbstractGPT: базовый интерфейс для GPT-моделей
- ApiGPT: реализация для HTTP API клиентов
- YandexGPT: конкретная реализация для YandexGPT
"""

import asyncio
import json
import logging
from abc import ABC, ABCMeta, abstractmethod
from typing import Dict

import aiohttp

from config import config

# Настройка логгера для модуля
logger = logging.getLogger(__name__)


class AbstractGPT(ABC):
    """Базовый абстрактный интерфейс для всех GPT-моделей.

    Определяет стандартные методы для взаимодействия с языковыми моделями,
    включая получение имени модели и генерацию текста.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Получить человекочитаемое имя модели.

        Returns:
            str: Имя модели
        """
        pass

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: str = "") -> Dict:
        """Генерация текста по промпту.

        Args:
            prompt (str): Основной промпт для генерации
            system_prompt (str, optional): Системный промпт для настройки поведения

        Returns:
            Dict: Сырой ответ модели в формате словаря

        Raises:
            Exception: При ошибках генерации или сетевых проблемах
        """
        pass


class ApiGPT(AbstractGPT, metaclass=ABCMeta):
    """Базовый класс для GPT-моделей, работающих через HTTP API.

    Предоставляет общую реализацию HTTP-клиента с обработкой ошибок,
    настройкой таймаутов и логированием запросов. Подходит для 
    интеграции с различными GPT-сервисами через REST API.

    Attributes:
        api_url (str): URL эндпоинта API
        headers (Dict[str, str]): HTTP-заголовки для запросов
        timeout (int): Таймаут запроса в секундах
    """

    def __init__(self, *, api_url: str, headers: Dict[str, str], timeout: int):
        """Инициализация API-клиента GPT.

        Args:
            api_url (str): Полный URL эндпоинта API
            headers (Dict[str, str]): HTTP-заголовки для авторизации
            timeout (int): Таймаут запроса в секундах
        """
        self.api_url = api_url
        self.headers = headers
        self.timeout = timeout

    @abstractmethod
    def build_payload(self, prompt: str, system_prompt: str) -> Dict:
        """Сформировать payload для API запроса.

        Метод должен создать структуру данных, специфичную для 
        конкретного GPT-сервиса, на основе промптов.

        Args:
            prompt (str): Основной промпт для генерации
            system_prompt (str): Системный промпт для настройки

        Returns:
            Dict: Payload для отправки в API
        """
        pass

    async def generate(self, prompt: str, system_prompt: str = "") -> Dict:
        """Генерация текста с автоматической обработкой HTTP-запроса.

        Создает payload, отправляет запрос и обрабатывает ответ с 
        логированием и обработкой ошибок.

        Args:
            prompt (str): Основной промпт для генерации
            system_prompt (str, optional): Системный промпт

        Returns:
            Dict: Сырой ответ от API в формате словаря

        Raises:
            Exception: При ошибках API, сети или парсинга ответа
        """
        logger.debug(f"Начало генерации для модели {self.model_name}")
        
        payload = self.build_payload(prompt, system_prompt)
        response = await self._make_request(payload)
        
        logger.info(f"Успешно получен ответ от модели {self.model_name}")
        return response

    async def _make_request(self, payload: Dict) -> Dict:
        """Выполнить HTTP-запрос к GPT API с обработкой ошибок.

        Универсальный метод для отправки POST-запросов с:
        - Логированием запросов и ответов
        - Обработкой HTTP-ошибок
        - Парсингом JSON-ответов  
        - Обработкой сетевых исключений

        Args:
            payload (Dict): Данные для отправки в API

        Returns:
            Dict: Распарсенный JSON-ответ

        Raises:
            Exception: При критических ошибках запроса
        """
        try:
            logger.debug(f"Отправка запроса к {self.model_name}")
            logger.debug(f"Размер payload: {len(json.dumps(payload))} символов")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    headers=self.headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(
                            f"HTTP ошибка {response.status} при обращении к {self.model_name}: {response_text[:200]}"
                        )
                        raise Exception(
                            f"{self.model_name} API error {response.status}: {response_text[:200]}"
                        )
                    
                    try:
                        result = json.loads(response_text)
                        logger.debug(f"Успешно распарсен JSON-ответ от {self.model_name}")
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(
                            f"Ошибка парсинга JSON от {self.model_name}: {e}. "
                            f"Сырый ответ: {response_text[:200]}"
                        )
                        raise Exception(f"Ошибка парсинга ответа от {self.model_name}: {str(e)}")
                    
        except asyncio.TimeoutError:
            logger.error(f"Превышен таймаут запроса к {self.model_name} ({self.timeout}s)")
            raise Exception(
                f"Превышено время ожидания ответа от {self.model_name}. "
                f"Попробуйте еще раз через минуту."
            )
        except aiohttp.ClientError as e:
            logger.error(f"Сетевая ошибка при обращении к {self.model_name}: {e}")
            raise Exception(f"Ошибка сети при подключении к {self.model_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при работе с {self.model_name}: {e}")
            raise


def get_yandexgpt_headers(api_key: str) -> Dict[str, str]:
    """Сформировать HTTP-заголовки для YandexGPT API.

    Создает стандартные заголовки для аутентификации в Yandex Cloud,
    включая авторизацию по API-ключу и указание JSON-формата.

    Args:
        api_key (str): API-ключ для доступа к YandexGPT

    Returns:
        Dict[str, str]: Словарь с HTTP-заголовками
    """
    return {
        "Content-Type": "application/json",
        "Authorization": f"Api-Key {api_key}",
    }


class YandexGPT(ApiGPT):
    """Клиент для работы с YandexGPT API.

    Специализированная реализация ApiGPT для интеграции с Yandex Cloud
    YandexGPT.
    """

    def __init__(self):
        """Инициализация клиента YandexGPT с настройками из конфига."""
        super().__init__(
            api_url=config.YANDEXGPT_API_URL,
            headers=get_yandexgpt_headers(config.YANDEXGPT_API_KEY),
            timeout=config.YANDEXGPT_TIMEOUT,
        )
        
        logger.debug(f"Инициализирован клиент {self.model_name}")

    @property
    def model_name(self) -> str:
        """Получить имя текущей модели YandexGPT.

        Returns:
            str: Строка с названием модели и версией
        """
        return f"YandexGPT ({config.YANDEXGPT_MODEL})"

    def build_payload(self, prompt: str, system_prompt: str) -> Dict:
        """Сформировать payload для YandexGPT API.

        Создает структуру данных согласно спецификации YandexGPT API,
        включая настройки генерации и промпты в правильном формате.

        Args:
            prompt (str): Основной промпт для генерации
            system_prompt (str): Системный промпт для настройки поведения

        Returns:
            Dict: Payload для YandexGPT API
        """
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
