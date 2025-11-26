"""
Инфраструктура генерации изображений с использованием ИИ.

Данный модуль предоставляет интерфейсы и реализации для генерации изображений
с помощью различных AI сервисов. Включает поддержку Fusion Brain API (Kandinsky)
для создания изображений по текстовым описаниям.

Основные компоненты:
- AbstractImageGenerator: Абстрактный интерфейс для генераторов изображений
- FusionBrainImageGenerator: Реализация для работы с Fusion Brain API
- create_fusion_brain_image_generator(): Фабричная функция для создания генератора

Модуль поддерживает асинхронную генерацию изображений с обработкой ошибок,
мониторингом статуса и конвертацией результатов в байты.
"""

import asyncio
import json
import logging
import base64
from abc import ABC, abstractmethod
from typing import Dict, Optional

import aiohttp
from aiohttp import FormData

from dtos import Dimensions

# Настройка логирования для модуля
logger = logging.getLogger(__name__)


class AbstractImageGenerator(ABC):
    """
    Базовый абстрактный класс для генераторов изображений.
    
    Определяет интерфейс для всех генераторов изображений,
    которые могут создавать визуальный контент по текстовому описанию
    с использованием различных AI сервисов.
    """

    @property
    @abstractmethod
    def model_name(self) -> str:
        """
        Возвращает имя модели генератора.
        
        Returns:
            str: Название модели для логирования и идентификации
        """
        pass

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        dimensions: Dimensions,
    ) -> bytes:
        """
        Генерирует изображение по текстовому описанию.
        
        Args:
            prompt (str): Текстовое описание желаемого изображения
            dimensions (Dimensions): Ширина и высота изображения в пикселях

        Returns:
            bytes: Байты сгенерированного изображения в формате PNG
            
        Raises:
            Exception: При ошибке генерации изображения или недоступности API
        """
        pass


class FusionBrainImageGenerator(AbstractImageGenerator):
    """
    Генератор изображений через Fusion Brain API (Kandinsky).
    
    Реализует генерацию изображений с помощью Kandinsky модели через
    Fusion Brain API. Поддерживает асинхронную генерацию, мониторинг
    статуса выполнения и конвертацию результатов в байты.
    
    Attributes:
        api_key (str): API ключ для доступа к Fusion Brain
        secret_key (str): Секретный ключ для авторизации
        api_url (str): Базовый URL API сервиса
        pipeline_id (str): ID пайплайна для генерации (может быть получен динамически)
        timeout (int): Таймаут запросов в секундах
        poll_interval (int): Интервал проверки статуса генерации в секундах
        max_poll_attempts (int): Максимальное количество попыток проверки статуса
        
    Note:
        Использует polling механизм для ожидания завершения генерации.
        Рекомендуется настроить разумные значения timeout и poll_interval.
    """

    def __init__(
        self,
        *,
        api_key: str,
        secret_key: str,
        api_url: str,
        pipeline_id: str,
        timeout: int,
        poll_interval: int,
        max_poll_attempts: int,
    ):
        """
        Инициализация генератора изображений Fusion Brain.
        
        Args:
            api_key (str): API ключ для доступа к Fusion Brain
            secret_key (str): Секретный ключ для авторизации
            api_url (str): Базовый URL API сервиса
            pipeline_id (str): ID пайплайна для генерации
            timeout (int): Таймаут HTTP запросов в секундах
            poll_interval (int): Интервал проверки статуса в секундах
            max_poll_attempts (int): Максимальное количество попыток
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.api_url = api_url.rstrip("/")
        self.pipeline_id = pipeline_id
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_poll_attempts = max_poll_attempts

    @property
    def model_name(self) -> str:
        """
        Возвращает название модели генератора.
        
        Returns:
            str: "Fusion Brain (Kandinski)"
        """
        return "Fusion Brain (Kandinski)"

    def _get_auth_headers(self) -> Dict[str, str]:
        """
        Формирует заголовки авторизации для Fusion Brain API.
        
        Fusion Brain использует специальный формат заголовков:
        - X-Key с префиксом "Key "
        - X-Secret с префиксом "Secret "
        
        Returns:
            Dict[str, str]: Словарь с заголовками авторизации
            
        Note:
            Если получаете 401 ошибку, проверьте:
            1. Правильность API ключа и Secret ключа
            2. Не истек ли срок действия ключей
            3. Что ключи активированы в личном кабинете Fusion Brain
        """
        headers = {
            "X-Key": f"Key {self.api_key}",
            "X-Secret": f"Secret {self.secret_key}",
        }
        logger.debug(f"Заголовки авторизации: X-Key=Key {self.api_key[:10]}..., X-Secret=Secret {self.secret_key[:10]}...")
        return headers
    
    async def get_pipeline_id(self) -> Optional[str]:
        """
        Получает ID доступного пайплайна для генерации.
        
        Запрашивает список доступных пайплайнов у API и возвращает
        ID первого доступного. Используется для динамического
        определения pipeline_id если он не был установлен.
        
        Returns:
            Optional[str]: ID первого доступного пайплайна или None при ошибке
            
        Note:
            Метод логирует результат для отладки проблем с API
        """
        headers = self._get_auth_headers()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/key/api/v1/pipelines",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        pipelines = await response.json()
                        if pipelines and len(pipelines) > 0:
                            pipeline_id = pipelines[0].get('id')
                            logger.info(f"Получен pipeline_id: {pipeline_id}")
                            return pipeline_id
                        else:
                            logger.warning("Список пайплайнов пуст")
                            return None
                    else:
                        response_text = await response.text()
                        logger.error(f"Не удалось получить список пайплайнов: {response.status}, {response_text}")
                        return None
        except Exception as e:
            logger.error(f"Ошибка при получении списка пайплайнов: {e}")
            return None

    async def _start_generation(
        self,
        prompt: str,
        width: int,
        height: int,
        images: int,
    ) -> str:
        """
        Запускает генерацию изображения и возвращает UUID задачи.
        
        Инициирует процесс генерации изображения через Fusion Brain API
        с заданными параметрами. Автоматически получает pipeline_id если
        он не был установлен.
        
        Args:
            prompt (str): Текстовое описание изображения
            width (int): Ширина изображения в пикселях
            height (int): Высота изображения в пикселях
            images (int): Количество изображений для генерации
            negative_prompt (Optional[str]): Негативный промпт для исключения элементов
            
        Returns:
            str: UUID задачи генерации для отслеживания статуса
            
        Raises:
            Exception: При ошибке запуска генерации или недоступности API
        """
        negative_prompt = ("размыто, низкое качество, плохая анатомия, искажения, артефакты, водяной знак, "
                           "текст, подпись, обрезано, уродливо, пикселизация")

        # Получаем pipeline_id если он не установлен
        pipeline_id = self.pipeline_id
        if not pipeline_id:
            logger.info("pipeline_id не установлен, получаем его динамически...")
            pipeline_id = await self.get_pipeline_id()
            if not pipeline_id:
                raise Exception("Не удалось получить pipeline_id. Проверьте API ключи и доступность сервиса.")
            self.pipeline_id = pipeline_id
        
        params = {
            "type": "GENERATE",
            "numImages": images,
            "width": width,
            "height": height,
            "negativePromptDecoder": negative_prompt,
            "generateParams": {
                "query": prompt
            }
        }
        
        data = FormData()
        data.add_field('pipeline_id', pipeline_id)
        data.add_field('params', json.dumps(params), content_type='application/json')

        headers = self._get_auth_headers()

        try:
            logger.info(f"Запуск генерации изображения: промпт='{prompt[:50]}...', размер={width}x{height}, pipeline_id={self.pipeline_id or 'не установлен'}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/key/api/v1/pipeline/run",
                    headers=headers,
                    data=data,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_text = await response.text()
                    
                    if response.status == 401:
                        logger.error(f"Ошибка авторизации (401). Проверьте:")
                        logger.error(f"1. Правильность API ключа и Secret ключа")
                        logger.error(f"2. Не истек ли срок действия ключей")
                        logger.error(f"3. Формат заголовков авторизации")
                        logger.error(f"Используемые заголовки: X-Key={self.api_key[:10]}..., X-Secret={self.secret_key[:10]}...")
                        raise Exception(f"{self.model_name} API error 401: Unauthorized. Проверьте правильность API ключей и Secret ключа.")
                    
                    if response.status != 200 and response.status - 200 > 99:  # Костылек
                        logger.error(f"Ошибка API {self.model_name}: {response.status}, {response_text}")
                        raise Exception(f"{self.model_name} API error {response.status}: {response_text}")
                    
                    try:
                        result = json.loads(response_text)
                        # Проверяем, не вернул ли сервис статус недоступности
                        if 'pipeline_status' in result:
                            status = result.get('pipeline_status')
                            raise Exception(f"Сервис недоступен: {status}")
                        
                        uuid = result.get('uuid')
                        if not uuid:
                            raise Exception(f"Не получен UUID от {self.model_name}: {response_text}")
                        logger.info(f"Генерация запущена, UUID: {uuid}")
                        return uuid
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON ответа: {e}, Сырой ответ: {response_text}")
                        raise Exception(f"Ошибка парсинга ответа от {self.model_name}: {str(e)}")
                        
        except asyncio.TimeoutError:
            logger.error(f"Таймаут запроса к {self.model_name}")
            raise Exception(f"Превышено время ожидания ответа от {self.model_name}. Попробуйте еще раз.")
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при запросе к {self.model_name}: {e}")
            raise Exception(f"Ошибка сети при подключении к {self.model_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при работе с {self.model_name}: {e}")
            raise

    async def _check_status(self, uuid: str) -> Dict:
        """
        Проверяет статус генерации по UUID.
        
        Запрашивает текущий статус задачи генерации у API
        и возвращает данные о состоянии.
        
        Args:
            uuid (str): UUID задачи генерации
            
        Returns:
            Dict: Данные о статусе генерации
            
        Raises:
            Exception: При ошибке проверки статуса или проблемах с API
        """
        headers = self._get_auth_headers()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.api_url}/key/api/v1/pipeline/status/{uuid}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    response_text = await response.text()
                    
                    if response.status != 200:
                        logger.error(f"Ошибка проверки статуса {self.model_name}: {response.status}, {response_text}")
                        raise Exception(f"{self.model_name} status check error {response.status}: {response_text}")
                    
                    try:
                        result = json.loads(response_text)
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"Ошибка парсинга JSON статуса: {e}, Сырой ответ: {response_text}")
                        raise Exception(f"Ошибка парсинга статуса от {self.model_name}: {str(e)}")
                        
        except asyncio.TimeoutError:
            logger.error(f"Таймаут проверки статуса {self.model_name}")
            raise Exception(f"Превышено время ожидания статуса от {self.model_name}.")
        except aiohttp.ClientError as e:
            logger.error(f"Ошибка сети при проверке статуса {self.model_name}: {e}")
            raise Exception(f"Ошибка сети при проверке статуса {self.model_name}: {str(e)}")

    async def _wait_for_completion(self, uuid: str) -> Dict:
        """
        Ожидает завершения генерации и возвращает результат.
        
        Использует polling механизм для мониторинга статуса генерации
        с настраиваемыми интервалами проверки и максимальным количеством попыток.
        
        Args:
            uuid (str): UUID задачи генерации
            
        Returns:
            Dict: Данные о завершенной генерации с результатами
            
        Raises:
            Exception: При ошибке генерации или превышении времени ожидания
        """
        logger.info(f"Ожидание завершения генерации, UUID: {uuid}")
        
        for attempt in range(self.max_poll_attempts):
            status_data = await self._check_status(uuid)
            status = status_data.get('status')
            
            if status == 'DONE':
                logger.info(f"Генерация завершена успешно, UUID: {uuid}")
                return status_data
            elif status == 'FAIL':
                error_message = status_data.get('errorDescription', status_data.get('error', 'Неизвестная ошибка'))
                logger.error(f"Генерация завершилась с ошибкой, UUID: {uuid}, ошибка: {error_message}")
                raise Exception(f"Ошибка генерации изображения: {error_message}")
            
            # Статус IN_PROGRESS или другой - продолжаем ожидание
            logger.debug(f"Генерация в процессе (попытка {attempt + 1}/{self.max_poll_attempts}), UUID: {uuid}")
            await asyncio.sleep(self.poll_interval)
        
        raise Exception(f"Превышено максимальное время ожидания генерации изображения (UUID: {uuid})")

    async def _get_image_bytes(self, image_base64: str) -> bytes:
        """
        Конвертирует base64 строку в байты изображения.
        
        Обрабатывает base64 данные изображения, убирает префиксы
        и конвертирует в байты для дальнейшего использования.
        
        Args:
            image_base64 (str): Строка с изображением в формате base64
            
        Returns:
            bytes: Байты изображения
            
        Raises:
            Exception: При ошибке декодирования base64 данных
        """
        try:
            # Убираем префикс data:image/...;base64, если есть
            if ',' in image_base64:
                image_base64 = image_base64.split(',')[1]
            
            image_bytes = base64.b64decode(image_base64)
            return image_bytes
        except Exception as e:
            logger.error(f"Ошибка декодирования base64 изображения: {e}")
            raise Exception(f"Ошибка декодирования изображения: {str(e)}")

    async def generate_image(
        self,
        prompt: str,
        dimensions: Dimensions,
    ) -> bytes:
        """
        Генерирует изображение по текстовому описанию.
        
        Args:
            prompt (str): Текстовое описание желаемого изображения
            dimensions (Dimensions): Ширина и высота изображения в пикселях

        Returns:
            bytes: Байты сгенерированного изображения в формате PNG

        Raises:
            Exception: При ошибке генерации изображения или недоступности API

        Note:
            Включает базовую предобработку промпта для улучшения качества генерации.
            Для более сложной обработки рекомендуется использовать отдельный prompt builder.
        """
        # Предобработка промпта, временное решение, позже нужно сделать полноценный prompt builder
        sections = [
                "качественное изображение, профессиональное фото, 4k, 8k, гиперреализм, высокая детализация, ",
                "f/1.8, боке, фотореалистичность, ISO 100, реальное изображение, ",
                "кинематографичное освещение, объемный свет, студийный свет, мягкое свечение, ray tracing"
            ]
        

        people_keys = ["человек", "люди", "мужчина", "женщина", "ребенок"]  # Переделать
        if any(word in prompt for word in people_keys):
            sections.append(", у людей нормальные руки и ноги, люди изображены отчетливо. ")

        prompt = "\n".join(sections).strip()

        width = dimensions.width
        height = dimensions.height
        images = 1

        # Запускаем генерацию
        uuid = await self._start_generation(prompt, width, height, images)
        
        # Ожидаем завершения
        result = await self._wait_for_completion(uuid)
        
        # Получаем изображение из результата
        # По документации API изображения находятся в result.result.files
        result_data = result.get('result', {})
        images_data = result_data.get('files', [])
        if not images_data:
            raise Exception("Не получены изображения в результате генерации")
        
        # Берем первое изображение
        first_image_base64 = images_data[0]
        image_bytes = await self._get_image_bytes(first_image_base64)
        
        logger.info(f"Успешно сгенерировано изображение, размер: {len(image_bytes)} байт")
        return image_bytes


