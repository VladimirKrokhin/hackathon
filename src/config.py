import os
from dotenv import load_dotenv
from typing import Dict, Any, Tuple, List

from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Config(BaseSettings):
    BOT_TOKEN: str = Field(default="", env="BOT_TOKEN")

    # YandexGPT настройки
    YANDEXGPT_API_KEY: str = Field(default="", env="YANDEXGPT_API_KEY") # API ключ из Yandex Cloud
    YANDEXGPT_CATALOG_ID: str = Field(default="", env="YANDEXGPT_CATALOG_ID") # ID каталога 

    # Параметры для YandexGPT
    YANDEXGPT_MODEL: str = Field(default="yandexgpt-5.1", env="YANDEXGPT_MODEL") # Модель из Yandex Cloud
    YANDEXGPT_TEMPERATURE: float = Field(default=0.5, env="YANDEXGPT_TEMPERATURE")
    YANDEXGPT_MAX_TOKENS: int = Field(default=2000, env="YANDEXGPT_MAX_TOKENS")
    YANDEXGPT_API_URL: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

    # Режим отладки
    DEBUG: bool = Field(default=False, env="DEBUG")
    
    # Таймауты
    YANDEXGPT_TIMEOUT: int = 30  # секунд
    PLAYWRIGHT_TIMEOUT: int = 60000  # 60 секунд

    # Размеры для соцсетей
    SOCIAL_MEDIA_SIZES: Dict[str, Dict[str, Dict[str, int]]] = {
        "📱 ВКонтакте (для молодежи)": {
            "post": {"width": 510, "height": 510},
        },
        "💬 Telegram (для взрослых/бизнеса)": {
            "post": {"width": 1200, "height": 630},
        },
        "🌐 Сайт/новостная рассылка": {
            "og": {"width": 1200, "height": 630},
        }
    }

    DEFAULT_SIZE: Tuple[int, int] = (1200, 630)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def validate_config(self) -> List[str]:
        """Проверка необходимых настроек"""
        errors = []
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN не установлен в .env файле")
        
        # Проверяем только если не в демо-режиме
        if not self.DEMO_MODE:
            if not self.YANDEXGPT_API_KEY:
                errors.append("YANDEXGPT_API_KEY не установлен в .env файле")
            if not self.YANDEXGPT_CATALOG_ID:
                errors.append("YANDEXGPT_CATALOG_ID не установлен в .env файле")
        
        return errors




config = Config()
