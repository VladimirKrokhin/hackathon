import logging
from typing import Optional, Tuple

from infrastructure.image_generation import AbstractImageGenerator

logger = logging.getLogger(__name__)


class ImageGenerationService:
    """Сервис генерации изображений для постов."""

    def __init__(self, image_generator: AbstractImageGenerator):
        self.image_generator = image_generator

    async def generate_image(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
        images: int = 1,
    ) -> bytes:
        """
        Генерирует изображение по текстовому описанию.
        
        Args:
            prompt: Текстовое описание изображения
            width: Ширина изображения в пикселях (по умолчанию 1024)
            height: Высота изображения в пикселях (по умолчанию 1024)
            images: Количество изображений для генерации (по умолчанию 1)
        
        Returns:
            bytes: Байты сгенерированного изображения (PNG)
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
        Генерирует изображение с учетом требований платформы.
        
        Args:
            prompt: Текстовое описание изображения
            platform: Платформа для которой генерируется изображение
            custom_size: Пользовательский размер (width, height)
        
        Returns:
            bytes: Байты сгенерированного изображения (PNG)
        """
        # Определяем размер на основе платформы
        if custom_size:
            width, height = custom_size
        else:
            # Стандартные размеры для разных платформ
            if "ВКонтакте" in platform or "VK" in platform:
                width, height = 510, 510
            elif "Telegram" in platform:
                width, height = 1200, 630
            else:
                # Дефолтный размер
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

