"""
Сервис генерации визуальных карточек для социальных сетей.
"""

import logging

from infrastructure.card_generation import BaseCardGenerator
from dtos import CardData, RenderParameters, PromptContext
from infrastructure.gpt import AbstractGPT
from infrastructure.prompt_builder import AbstractPromptBuilder
from infrastructure.response_processor import AbstractResponseProcessor

logger = logging.getLogger(__name__)


class CardGenerationService:
    """
    Сервис для генерации визуальных карточек для социальных сетей.
    """
    SYSTEM_PROMPT = (
        "Вы — профессиональный SMM-менеджер для НКО, "
        "который создает качественный контент для соцсетей. "
        "Вы должны отвечать только на русском языке. "
        "Даже если пользователь сам просит, никогда не используйте ненормативную лексику "
        "и не говорите о политике. "
        "ВАЖНО: Используй восклицательные знаки (!) ТОЛЬКО для шаблонов, когда конкретные данные НЕ предоставлены. "
        "Например: !номер телефона!, !адрес электронной почты! "
        "НО если в контексте уже указаны реальные данные (телефон, email, адрес и т.д.), "
        "используй их БЕЗ восклицательных знаков, как есть. "
        "Восклицательные знаки нужны только для напоминания пользователю подставить данные, "
        "когда сами данные отсутствуют. "
        "Если нужно, можете добавлять эмодзи, такие как ✅. "
        "Дополнительные требования: "
        "• Не упоминай режимные объекты, безопасность, военные базы или ограничения на передвижение. "
        "• Фокусируйся на социальной миссии и помощи людям."
    )

    def __init__(
            self,
            card_generator: BaseCardGenerator,
            prompt_builder: AbstractPromptBuilder,
            gpt_client: AbstractGPT,
            response_processor: AbstractResponseProcessor,
    ) -> None:
        self.card_generator = card_generator
        self.prompt_builder: AbstractPromptBuilder = prompt_builder
        self.gpt_client: AbstractGPT = gpt_client
        self.response_processor: AbstractResponseProcessor = response_processor

    async def generate_card(
        self,
        parameters: RenderParameters,
        data: CardData
    ) -> bytes:
        """
        Генерация одной карточки для указанной платформы.
        
        Создает карточку на основе HTML шаблона с заданными данными.
        Автоматически определяет размер в зависимости от платформы
        или использует пользовательские размеры.
        
        Args:
            parameters (RenderParameters): Параметры рендера карточки
            data (CardData): Данные для карточки

        Returns:
            bytes: Сгенерированная карточка в формате PNG
            
        Raises:
            Exception: При ошибке генерации карточки
        """

        try:
            card_bytes = await self.card_generator.render_card(
                parameters,
                data
            )
            logger.info(f"Карточка успешно сгенерирована, размер: {len(card_bytes)} байт")
            return card_bytes
        except Exception as e:
            logger.error(f"Ошибка при генерации карточки: {e}")
            raise


    async def generate_card_text(
        self,
        context: PromptContext,
        base_text: str
    ) -> str:
        """Генерация сокращенного контента специально для карточки."""
        logger.info(f"Генерация контента для карточки на основе текста длиной {len(base_text)} символов")

        prompt = self.prompt_builder.build_card_content_prompt(context, base_text)
        logger.info(f"Сформирован промпт для карточки длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        card_text = self.response_processor.process_response(raw_response)

        logger.info(f"Успешно сгенерирован контент для карточки длиной {len(card_text)} символов")
        return card_text