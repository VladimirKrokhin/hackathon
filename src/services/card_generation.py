import logging
from typing import Dict, List, Optional, Tuple

from infrastructure.card_generation import BaseCardGenerator, PILCardGenerator
from config import config

logger = logging.getLogger(__name__)


class CardGenerationService:
    """Сервис генерации визуальных карточек для соцсетей."""

    def __init__(self, card_generator: BaseCardGenerator):
        self.card_generator = card_generator

    def _get_size_for_platform(
        self,
        platform: str,
        card_type: str = "post",
        custom_size: Optional[Tuple[int, int]] = None,
    ) -> Tuple[int, int]:
        """Определение размера на основе платформы и типа карточки."""
        if custom_size:
            return custom_size

        # Находим конфигурацию для платформы
        for platform_key, sizes in config.SOCIAL_MEDIA_SIZES.items():
            if platform_key in platform or platform in platform_key:
                # Определяем тип карточки
                if card_type == "story" and "story" in sizes:
                    return (sizes["story"]["width"], sizes["story"]["height"])
                elif card_type == "square" and "post_square" in sizes:
                    return (
                        sizes["post_square"]["width"],
                        sizes["post_square"]["height"],
                    )
                elif "post" in sizes:
                    return (sizes["post"]["width"], sizes["post"]["height"])
                elif "og" in sizes:
                    return (sizes["og"]["width"], sizes["og"]["height"])
                break

        # Дефолтные размеры
        return config.DEFAULT_SIZE

    async def generate_card(
        self,
        template_name: str,
        data: Dict,
        platform: str,
        card_type: str = "post",
        custom_size: Optional[Tuple[int, int]] = None,
    ) -> bytes:
        """Генерация одной карточки."""
        size = self._get_size_for_platform(platform, card_type, custom_size)
        logger.info(
            f"Генерация карточки: шаблон={template_name}, "
            f"платформа={platform}, тип={card_type}, размер={size}"
        )

        try:
            card_bytes = await self.card_generator.render_card(
                template_name=template_name,
                data=data,
                size=size,
            )
            logger.info(f"Карточка успешно сгенерирована, размер: {len(card_bytes)} байт")
            return card_bytes
        except Exception as e:
            logger.error(f"Ошибка при генерации карточки: {e}")
            raise

    async def generate_multiple_cards(
        self,
        template_name: str,
        data: Dict,
        platform: str,
        card_types: Optional[List[str]] = None,
        custom_sizes: Optional[Dict[str, Tuple[int, int]]] = None,
    ) -> Dict[str, bytes]:
        """Генерация нескольких карточек для разных типов."""
        card_types = card_types or ["post"]
        logger.info(
            f"Генерация {len(card_types)} карточек: "
            f"шаблон={template_name}, платформа={platform}, типы={card_types}"
        )

        results: Dict[str, bytes] = {}
        for card_type in card_types:
            try:
                size_override = (
                    custom_sizes.get(card_type) if custom_sizes else None
                )
                results[card_type] = await self.generate_card(
                    template_name=template_name,
                    data=data,
                    platform=platform,
                    card_type=card_type,
                    custom_size=size_override,
                )
            except Exception as e:
                logger.error(
                    f"Ошибка при генерации карточки типа {card_type}: {e}"
                )
                raise

        if not results:
            raise ValueError("Не удалось сгенерировать ни одной карточки")

        logger.info(f"Успешно сгенерировано {len(results)} карточек")
        return results
