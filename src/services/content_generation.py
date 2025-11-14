from typing import Dict, Union

from infrastructure.prompt_builder import AbstractPromptBuilder, PromptContext
from infrastructure.response_processor import AbstractResponseProcessor
from infrastructure.gpt import AbstractGPT

import logging
from typing import Dict, Union

logger = logging.getLogger(__name__)



class ContentGenerationService:
    """Cервис генерации текстового контента медиа."""

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

    async def generate_content(
        self, user_data: Union[Dict, PromptContext], user_text: str
    ) -> str:
        context = (
            user_data
            if isinstance(user_data, PromptContext)
            else PromptContext.from_dict(user_data or {})
        )
        prompt = self.prompt_builder.build_prompt(context, user_text)
        raw_response = await self.gpt_client.generate(prompt)
        return self.response_processor.process_response(raw_response)

