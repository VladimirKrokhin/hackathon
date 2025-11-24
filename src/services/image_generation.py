"""
Сервис генерации изображений для социальных сетей.

Данный модуль предоставляет высокоуровневый интерфейс для создания
изображений на основе текстовых описаний с использованием ИИ.
Поддерживает генерацию изображений различных размеров для разных
социальных платформ.
"""

import logging
from typing import Optional, Tuple

from infrastructure.image_generation import AbstractImageGenerator

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """
    Сервис для генерации изображений для постов и карточек.
    
    Предоставляет удобный интерфейс для создания изображений с помощью
    различных генераторов изображений (например, FusionBrain).
    Автоматически определяет оптимальные размеры в зависимости от
    целевой социальной платформы.
    
    Поддерживает:
    - Генерацию изображений по текстовому описанию
    - Автоматический подбор размеров под платформы
    - Настраиваемые размеры изображений
    - Пакетную генерацию нескольких изображений
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
        width: int = 1024,
        height: int = 1024,
        images: int = 1,
    ) -> bytes:
        """
        Генерация изображения по текстовому описанию.
        
        Создает изображение на основе детального текстового описания
        с использованием искусственного интеллекта. Поддерживает
        генерацию изображений различных размеров и количества.
        
        Args:
            prompt (str): Детальное текстовое описание желаемого изображения
            width (int): Ширина изображения в пикселях (по умолчанию 1024)
            height (int): Высота изображения в пикселях (по умолчанию 1024)
            images (int): Количество изображений для генерации (по умолчанию 1)
            
        Returns:
            bytes: Байты сгенерированного изображения в формате PNG
            
        Raises:
            Exception: При ошибке генерации изображения
        """
        logger.info(
            f"Генерация изображения: промпт='{prompt[:50]}...', "
            f"размер={width}x{height}, количество={images}"
        )

        try:
            image_bytes = await self.image_generator.generate(
                prompt=prompt,
                width=width,
                height=height,
                images=images,
            )
            logger.info(
                f"Успешно сгенерировано изображение, размер: {len(image_bytes)} байт"
            )
            return image_bytes
        except Exception as e:
            logger.error(f"Ошибка при генерации изображения: {e}")
            raise

    async def generate_image_for_platform(
        self,
        prompt: str,
        platform: str,
        custom_size: Optional[Tuple[int, int]] = None,
    ) -> bytes:
        """
        Генерация изображения с учетом требований социальной платформы.
        
        Создает изображение, оптимизированное под конкретную социальную
        платформу с автоматическим выбором подходящих размеров.
        Поддерживает пользовательские размеры для специальных случаев.
        
        Args:
            prompt (str): Текстовое описание для генерации изображения
            platform (str): Название целевой социальной платформы
            custom_size (Optional[Tuple[int, int]]): 
                Пользовательские размеры (ширина, высота)
                
        Returns:
            bytes: Байты сгенерированного изображения в формате PNG
            
        Raises:
            Exception: При ошибке генерации изображения
        """
        # Определение размера на основе платформы
        if custom_size:
            width, height = custom_size
        else:
            # Стандартные размеры для разных платформ
            if "ВКонтакте" in platform or "VK" in platform:
                width, height = 510, 510
            elif "Telegram" in platform:
                width, height = 1200, 630
            else:
                # Размер по умолчанию
                width, height = 1024, 1024

        logger.info(
            f"Генерация изображения для платформы '{platform}': "
            f"промпт='{prompt[:50]}...', размер={width}x{height}"
        )

        return await self.generate_image(
            prompt=prompt,
            width=width,
            height=height,
            images=1,
        )
