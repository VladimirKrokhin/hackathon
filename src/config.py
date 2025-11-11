import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # YandexGPT настройки
    YANDEXGPT_API_KEY = os.getenv("YANDEXGPT_API_KEY", "")  # API ключ из Yandex Cloud
    YANDEXGPT_CATALOG_ID = os.getenv("YANDEXGPT_CATALOG_ID", "")  # ID каталога (folder_id)
    
    # Правильные параметры для YandexGPT
    YANDEXGPT_MODEL = "yandexgpt-lite"  # или "yandexgpt"
    YANDEXGPT_API_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # Таймауты
    YANDEXGPT_TIMEOUT = 30  # секунд
    PLAYWRIGHT_TIMEOUT = 60000  # 60 секунд
    
    # Размеры для соцсетей
    SOCIAL_MEDIA_SIZES = {
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
    
    DEFAULT_SIZE = (1200, 630)  # Универсальный размер
    
    def validate_config(self):
        """Проверка необходимых настроек"""
        errors = []
        if not self.BOT_TOKEN:
            errors.append("❌ BOT_TOKEN не установлен в .env файле")
        
        # Проверяем только если не в демо-режиме
        if not os.getenv("DEMO_MODE", "False").lower() == "true":
            if not self.YANDEXGPT_API_KEY:
                errors.append("❌ YANDEXGPT_API_KEY не установлен в .env файле")
            if not self.YANDEXGPT_CATALOG_ID:
                errors.append("❌ YANDEXGPT_CATALOG_ID не установлен в .env файле")
        
        return errors
    
    def get_yandexgpt_headers(self):
        """Правильные заголовки для YandexGPT API"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Api-Key {self.YANDEXGPT_API_KEY}",
        }

config = Config()