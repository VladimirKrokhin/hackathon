import logging

from infrastructure.prompt_builder import AbstractPromptBuilder
from dtos import PromptContext, EditPromptContext
from infrastructure.response_processor import AbstractResponseProcessor
from infrastructure.gpt import AbstractGPT

logger = logging.getLogger(__name__)

class TextGenerationService:
    """Сервис генерации текстового контента медиа."""

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
        "НЕ ИСПОЛЬЗУЙ одиночные звездочки '*' или подчеркивания '_' НИ В КОЕМ СЛУЧАЕ!"
        "Если нужно, можете добавлять эмодзи, такие как ✅. "
        "Дополнительные требования: "
        "• Не упоминай режимные объекты, безопасность, военные базы или ограничения на передвижение. "
        "• Фокусируйся на социальной миссии и помощи людям."
    )

    def __init__(
        self,
        prompt_builder: AbstractPromptBuilder,
        gpt_client: AbstractGPT,
        response_processor: AbstractResponseProcessor,
    ) -> None:
        self.prompt_builder: AbstractPromptBuilder = prompt_builder
        self.gpt_client: AbstractGPT = gpt_client
        self.response_processor: AbstractResponseProcessor = response_processor

    async def generate_text(
        self,
        context: PromptContext,
        user_prompt: str
    ) -> str:
        logger.info(f"Генерация нового контента для цели: {context.goal}")

        prompt = self.prompt_builder.build_text_content_prompt(context, user_prompt)
        logger.info(f"Сформирован промпт длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        generated_text = self.response_processor.process_response(raw_response)

        logger.info(f"Успешно сгенерирован контент длиной {len(generated_text)} символов")
        return generated_text

    # TODO: Разберись что использовать: refactor_text() или edit_text()

    async def refactor_text(
        self,
        context: PromptContext,
        post_to_edit: str,
        user_prompt: str,
    ) -> str:
        """Редактирование существующего контента по запросу пользователя."""
        logger.info(f"Редактирование контента для цели: {context.goal}")

        prompt = self.prompt_builder.build_refactor_text_content_prompt(
            context, post_to_edit, user_prompt
        )
        logger.info(f"Сформирован промпт для редактирования длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        refactored_text = self.response_processor.process_response(raw_response)

        logger.info(
            f"Успешно отредактирован контент длиной {len(refactored_text)} символов"
        )
        return refactored_text

    async def edit_text(
        self,
        context: EditPromptContext
    ) -> str:
        logger.info(f"Редактирование текста пользователя.")

        prompt = self.prompt_builder.build_edit_text_prompt(context)
        logger.info(f"Сформирован промпт длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        generated_text = self.response_processor.process_response(raw_response)

        logger.info(f"Успешно сгенерирован исправленный вариант длиной {len(generated_text)} символов")
        return generated_text




