"""
Сервис генерации визуальных карточек для социальных сетей.

Данный модуль предоставляет высокоуровневый интерфейс для создания
карточек различного типа для разных социальных платформ.
Обеспечивает автоматическое определение размеров карточек в зависимости
от платформы и типа контента.
"""

import logging
from typing import Dict, List, Optional, Tuple

from infrastructure.card_generation import BaseCardGenerator, PILCardGenerator
from config import config

logger = logging.getLogger(__name__)


class CardGenerationService:
    """
    Сервис для генерации визуальных карточек для социальных сетей.
    
    Предоставляет удобный интерфейс для создания карточек различных
    типов и размеров для разных социальных платформ. Автоматически
    определяет оптимальные размеры в зависимости от платформы
    и типа контента.
    
    Поддерживает:
    - Генерацию одиночных карточек
    - Пакетную генерацию нескольких типов карточек
    - Настраиваемые размеры
    - Автоматическое определение размеров для платформ
    """

    def __init__(self, card_generator: BaseCardGenerator):
        """
        Инициализация сервиса генерации карточек.
        
        Args:
            card_generator (BaseCardGenerator): Генератор карточек (PIL или Playwright)
        """
        self.card_generator = card_generator

    def _get_size_for_platform(
        self,
        platform: str,
        card_type: str = "post",
        custom_size: Optional[Tuple[int, int]] = None,
    ) -> Tuple[int, int]:
        """
        Определение размера карточки на основе платформы и типа.
        
        Автоматически выбирает оптимальные размеры карточки в зависимости
        от целевой социальной платформы и типа контента.
        
        Args:
            platform (str): Название социальной платформы
            card_type (str): Тип карточки ('post', 'story', 'square', 'og')
            custom_size (Optional[Tuple[int, int]]): Пользовательский размер
            
        Returns:
            Tuple[int, int]: Размер карточки (ширина, высота)
        """
        if custom_size:
            return custom_size

        # Поиск конфигурации для платформы
        for platform_key, sizes in config.SOCIAL_MEDIA_SIZES.items():
            if platform_key in platform or platform in platform_key:
                # Определение типа карточки
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

        # Размеры по умолчанию
        return config.DEFAULT_SIZE

    async def generate_card(
        self,
        template_name: str,
        data: Dict,
        platform: str,
        card_type: str = "post",
        custom_size: Optional[Tuple[int, int]] = None,
    ) -> bytes:
        """
        Генерация одной карточки для указанной платформы.
        
        Создает карточку на основе HTML шаблона с заданными данными.
        Автоматически определяет размер в зависимости от платформы
        или использует пользовательские размеры.
        
        Args:
            template_name (str): Имя HTML шаблона для рендеринга
            data (Dict): Данные для подстановки в шаблон карточки
            platform (str): Целевая социальная платформа
            card_type (str): Тип карточки ('post', 'story', 'square', 'og')
            custom_size (Optional[Tuple[int, int]]): Пользовательские размеры
            
        Returns:
            bytes: Сгенерированная карточка в формате PNG
            
        Raises:
            Exception: При ошибке генерации карточки
        """
        size = self._get_size_for_platform(platform, card_type, custom_size)
        logger.info(
            f"Генерация карточки: шаблон={template_name}, "
            f"платформа={platform}, тип={card_type}, размер={size}"
        )

        try:
            generator = self.card_generator

            card_bytes = await generator.render_card(
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
        """
        Генерация нескольких карточек для разных типов контента.
        
        Создает набор карточек различного типа для одной платформы.
        Полезно для создания адаптивного контента под разные форматы
        публикации (обычные посты, истории, квадратные форматы).
        
        Args:
            template_name (str): Имя HTML шаблона для рендеринга
            data (Dict): Данные для подстановки в шаблоны
            platform (str): Целевая социальная платформа
            card_types (Optional[List[str]]): Список типов карточек для генерации
            custom_sizes (Optional[Dict[str, Tuple[int, int]]]): 
                Пользовательские размеры для каждого типа карточек
                
        Returns:
            Dict[str, bytes]: Словарь сгенерированных карточек, 
                             где ключ - тип карточки, значение - bytes изображения
                             
        Raises:
            ValueError: Если не удалось сгенерировать ни одной карточки
            Exception: При ошибке генерации любой из карточек
        """
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
