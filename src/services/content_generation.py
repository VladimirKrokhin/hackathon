import logging
from typing import Dict, Union

from infrastructure.prompt_builder import AbstractPromptBuilder, PromptContext, PlanPromptContext
from infrastructure.response_processor import AbstractResponseProcessor
from infrastructure.gpt import AbstractGPT

logger = logging.getLogger(__name__)



class TextContentGenerationService:
    """Cервис генерации текстового контента медиа."""

    SYSTEM_PROMPT = (
        "Вы — профессиональный SMM-менеджер для НКО, "
        "который создает качественный контент для соцсетей. "
        "Вы должны отвечать только на русском языке. "
        "Даже если пользователь сам просит, никогда не используйте ненормативную лексику "
        "и не говорите о политике. "
        "Там, где пользователь должен подставить нужные данные, "
        "указывай через восклицательные знаки в таком формате: "
        "!номер телефона!, !адрес электронной почты! "
        "Если нужно, можете добавлять емодзи, такие как ✅. "
        "Дополнительные требования: "
        "• Не упоминай режимные объекты, безопасность, военные базы или ограничения на передвижение. "
        "• Фокусируйся на социальной миссии и помощи людям."
    )

    def __init__(
        self,
        *,
        prompt_builder: AbstractPromptBuilder,
        gpt_client: AbstractGPT,
        response_processor: AbstractResponseProcessor,
    ):
        self.prompt_builder = prompt_builder
        self.gpt_client = gpt_client
        self.response_processor = response_processor

    async def generate_text_content(
        self, user_data: Union[Dict, PromptContext], user_text: str
    ) -> str:
        context = (
            user_data
            if isinstance(user_data, PromptContext)
            else PromptContext.from_dict(user_data or {})
        )
        logger.info(f"Генерация нового контента для цели: {context.goal}")

        prompt = self.prompt_builder.build_text_content_prompt(context, user_text)
        logger.info(f"Сформирован промпт длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        generated_text = self.response_processor.process_response(raw_response)

        logger.info(f"Успешно сгенерирован контент длиной {len(generated_text)} символов")
        return generated_text

    async def refactor_text_content(
        self,
        user_data: Union[Dict, PromptContext],
        generated_post: str,
        user_text: str,
    ) -> str:
        """Редактирование существующего контента по запросу пользователя."""
        context = (
            user_data
            if isinstance(user_data, PromptContext)
            else PromptContext.from_dict(user_data or {})
        )
        logger.info(f"Редактирование контента для цели: {context.goal}")

        prompt = self.prompt_builder.build_refactor_text_content_prompt(
            context, generated_post, user_text
        )
        logger.info(f"Сформирован промпт для редактирования длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        refactored_text = self.response_processor.process_response(raw_response)

        logger.info(
            f"Успешно отредактирован контент длиной {len(refactored_text)} символов"
        )
        return refactored_text

    async def generate_content_plan(
        self,
        user_data: Union[Dict, PlanPromptContext]
    ) -> str:
        context = (
            user_data
            if isinstance(user_data, PlanPromptContext)
            else PlanPromptContext.from_dict(user_data or {})
        )

        logger.info(f"Генерация контент-плана.")

        prompt = self.prompt_builder.build_content_plan_prompt(context)
        logger.info(f"Сформирован промпт длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        generated_text = self.response_processor.process_response(raw_response)

        logger.info(f"Успешно сгенерирован контент-план длиной {len(generated_text)} символов")
        return generated_text
