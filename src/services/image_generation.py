"""
Сервис генерации изображений для социальных сетей.

Данный модуль предоставляет высокоуровневый интерфейс для создания
изображений на основе текстовых описаний с использованием ИИ.
Поддерживает генерацию изображений различных размеров для разных
социальных платформ.
"""

import logging


from dtos import Dimensions
from infrastructure.image_generation import AbstractImageGenerator

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """
    Сервис для генерации изображений для постов и карточек.
    """

    def __init__(self, image_generator: AbstractImageGenerator):
        """
        Инициализация сервиса генерации изображений.
        
        Args:
            image_generator (AbstractImageGenerator): Генератор изображений
        """
        self.image_generator = image_generator

    async def generate_image(
        self,
        prompt: str,
        dimensions: Dimensions,
    ) -> bytes:
        """
        Генерация изображения по текстовому описанию.
        
        Создает изображение на основе детального текстового описания
        с использованием искусственного интеллекта. Поддерживает
        генерацию изображений различных размеров и количества.
        
        Args:
            prompt (str): Детальное текстовое описание желаемого изображения
            dimensions (Dimensions): Ширина и высота изображения в пикселях

        Returns:
            bytes: Байты сгенерированного изображения в формате PNG
            
        Raises:
            Exception: При ошибке генерации изображения
        """

        try:
            image_bytes = await self.image_generator.generate_image(
                prompt=prompt,
                dimensions=dimensions,
            )
            logger.info(
                f"Успешно сгенерировано изображение, размер: {len(image_bytes)} байт"
            )
            return image_bytes
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
            raise

