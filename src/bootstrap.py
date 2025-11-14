from typing import Any, Callable

from playwright.async_api import async_playwright, Browser

from infrastructure.prompt_builder import YandexGPTPromptBuilder
from infrastructure.response_processor import YandexGPTResponseProcessor
from services.content_generation import ContentGenerationService
from infrastructure.gpt import YandexGPT


async def init_browser() -> tuple[Browser, Any]:
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--single-process",
        ],
    )
    return browser, playwright


async def close_browser(browser: Browser, playwright) -> None:
    await browser.close()
    await playwright.stop()


def build_yandexgpt_content_generation_service() -> Callable[[], ContentGenerationService]:

    response_processor = YandexGPTResponseProcessor()
    gpt_client = YandexGPT()
    prompt_builder = YandexGPTPromptBuilder()

    service = ContentGenerationService(
        prompt_builder=prompt_builder,
        gpt_client=gpt_client,
        response_processor=response_processor,
    )

    return service






get_content_generation_service = build_yandexgpt_content_generation_service