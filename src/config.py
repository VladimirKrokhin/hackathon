"""
Конфигурация приложения
"""

from typing import Tuple, List
from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Загружает переменные окружения из файла .env
load_dotenv()


class Config(BaseSettings):
    """
    Настройки приложения
    """
    
    # Конфигурация бота Telegram
    BOT_TOKEN: str = Field(default="", env="BOT_TOKEN", description="Telegram bot токен")

    # Конфигурация YandexGPT API
    YANDEXGPT_API_KEY: str = Field(
        default="", 
        env="YANDEXGPT_API_KEY",
        description="API ключ для Yandex Cloud"
    )
    YANDEXGPT_CATALOG_ID: str = Field(
        default="", 
        env="YANDEXGPT_CATALOG_ID",
        description="Yandex Cloud catalog ID"
    )
    YANDEXGPT_MODEL: str = Field(
        default="yandexgpt-5.1", 
        env="YANDEXGPT_MODEL",
        description="YandexGPT модель"
    )
    YANDEXGPT_TEMPERATURE: float = Field(
        default=0.5, 
        env="YANDEXGPT_TEMPERATURE",
        description="Температура модели (0.0-1.0)"
    )
    YANDEXGPT_MAX_TOKENS: int = Field(
        default=2000, 
        env="YANDEXGPT_MAX_TOKENS",
        description="Максимальное количество токенов в ответе"
    )
    YANDEXGPT_API_URL: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    YANDEXGPT_TIMEOUT: int = Field(
        default=60, 
        env="YANDEXGPT_TIMEOUT",
        description="Таймаут для запроса Yandex GPT"
    )

    # Конфигурация FusionBrain API
    FUSION_BRAIN_API_KEY: str = Field(
        default="", 
        env="FUSION_BRAIN_API_KEY",
        description="FusionBrain API ключ"
    )
    FUSION_BRAIN_SECRET_KEY: str = Field(
        default="", 
        env="FUSION_BRAIN_SECRET_KEY",
        description="FusionBrain secret ключ"
    )
    FUSION_BRAIN_API_URL: str = Field(
        default="https://api-key.fusionbrain.ai/", 
        env="FUSION_BRAIN_API_URL",
        description="FusionBrain API endpoint"
    )
    FUSION_BRAIN_TIMEOUT: int = Field(
        default=60, 
        env="FUSION_BRAIN_TIMEOUT",
        description="FusionBrain таймаут в секундах"
    )
    FUSION_BRAIN_POLL_INTERVAL: int = Field(
        default=10, 
        env="FUSION_BRAIN_POLL_INTERVAL",
        description="Интервал опроса для генерации изображений в секундах"
    )
    FUSION_BRAIN_MAX_POLL_ATTEMPTS: int = Field(
        default=10, 
        env="FUSION_BRAIN_MAX_POLL_ATTEMPTS",
        description="Максимальное количество опросов для генерации изображений"
    )

    # Настройки Application 
    DEBUG: bool = Field(
        default=False, 
        env="DEBUG",
        description="Debug-режим"
    )

    # Настройки уведомлений контент-плана
    NOTIFICATION_CHECK_INTERVAL: int = Field(
        default=1,
        env="NOTIFICATION_CHECK_INTERVAL",
        description="Интервал проверки уведомлений в минутах"
    )
    NOTIFICATION_TIME_BEFORE: int = Field(
        default=60, 
        env="NOTIFICATION_TIME_BEFORE",
        description="За сколько минут до публикации отправлять уведомление"
    )

    DEFAULT_SIZE: Tuple[int, int] = (1200, 630)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    def validate_config(self) -> List[str]:
        """
        Производит валидацию поступаемых параметов.
        
        Returns:
            List[str]: Список ошибок, пуст если нет
        """
        errors = []
        if not self.BOT_TOKEN:
            errors.append("BOT_TOKEN не установлен в файле .env")
        if not self.YANDEXGPT_API_KEY:
            errors.append("YANDEXGPT_API_KEY не установлен в файле .env")
        if not self.YANDEXGPT_CATALOG_ID:
            errors.append("YANDEXGPT_CATALOG_ID не установлен в файле .env")
        return errors


# Глобальная сущность конфигурации
# TODO: переделай на Singleton
config = Config()
