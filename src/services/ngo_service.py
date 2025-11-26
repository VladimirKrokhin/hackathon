"""
Сервис бизнес-логики для работы с данными некоммерческих организаций.
"""

from typing import Optional, Tuple
import logging

from infrastructure.repositories.ngo_repository import AbstractNGORepository

from models import Ngo

# Настройка логгера для модуля
logger = logging.getLogger(__name__)




class NGOService:
    """Сервис для управления данными некоммерческих организаций.
    
    Обеспечивает бизнес-логику для работы с информацией о НКО,
    включая CRUD-операции, валидацию данных и формирование
    пользовательских представлений.
    """
    
    def __init__(self, repository: AbstractNGORepository):
        """Инициализация сервиса работы с НКО.
        
        Args:
            repository (AbstractNGORepository): Экземпляр репозитория для работы с БД
        """
        self.repository: AbstractNGORepository = repository
        logger.debug("Инициализирован сервис работы с НКО")

    def get_ngo_data_by_user_id(self, user_id: int) -> Ngo:
        """Получить данные о НКО пользователя.
        
        Извлекает информацию о НКО для указанного пользователя из базы данных
        и возвращает структурированный словарь с данными. Возвращает None
        если данные не найдены или произошла ошибка.

        Args:
            user_id (int): Идентификатор пользователя в Telegram

        Returns:
            Ngo: Данные НКО
        """
        logger.debug(f"Запрос данных НКО для пользователя {user_id}")
        ngo_data = self.repository.get_by_user_id(user_id)

        logger.info(f"Найдены данные НКО '{ngo_data.name}' для пользователя {user_id}")
        return ngo_data

    def create_ngo(self, ngo_data: Ngo) -> None:
        """Создать новые данные о НКО.
        
        Создает новую запись о НКО.

        Args:
            ngo_data (Ngo): Данные о НКО

        """
        logger.info(f"Создание новых данных НКО для пользователя {ngo_data.user_id}")
        self.repository.create(ngo_data)

    def update_ngo(self, ngo_data: Ngo) -> None:
        """Обновить данные о НКО.

        Обновляет запись о НКО.

        Args:
            ngo_data (Ngo): Данные о НКО
        """
        logger.info(f"Обновление данных НКО для пользователя {ngo_data.user_id}")
        self.repository.update(ngo_data)

    def delete_ngo(self, user_id: int) -> None:
        """Удалить данные о НКО пользователя.
        
        Args:
            user_id (int): Идентификатор пользователя в Telegram
        """
        logger.info(f"Даление данных НКО для пользователя {user_id}")
        return self.repository.delete_by_user_id(user_id)

    def ngo_exists(self, user_id: int) -> bool:
        """Проверить существование данных о НКО для пользователя.
        
        Быстрая проверка наличия данных о НКО для указанного пользователя.
        Используется для определения необходимости создания или обновления данных.

        Args:
            user_id (int): Идентификатор пользователя в Telegram
        """
        exists = self.repository.is_exists_by_user_id(user_id)
        logger.debug(f"Проверка существования НКО для пользователя {user_id}: {exists}")
        return exists


    def validate_ngo_data(self, ngo_data: Ngo) -> Tuple[bool, Optional[tuple[...]]]:
        """Валидация данных о НКО.
        
        Выполняет комплексную проверку корректности данных о НКО,
        включая проверку обязательных полей, длины строк и формата.
        Возвращает статус валидности и сообщение об ошибке.

        Args:
            ngo_data (Ngo): Данные о НКО для проверки

        Returns:
            Tuple[bool, Optional[tuple[str, ...]]]: Кортеж (статус_валидности, кортеж (сообщение_об_ошибке, ...))
        """
        # TODO: переделай с помощью Pydantic на саму модель
        logger.debug(f"Валидация данных НКО: {ngo_data}")

        messages = []
        
        # Проверка обязательного поля - название НКО
        ngo_name = ngo_data.name
        if not ngo_name:
            logger.debug("Валидация: пустое название НКО")
            messages += "Название НКО обязательно для заполнения"
        
        # Проверка длины названия
        if len(ngo_name) > 255:
            logger.debug(f"Валидация: слишком длинное название НКО ({len(ngo_name)} символов)")
            messages += "Название НКО слишком длинное (максимум 255 символов)"
        
        # Проверка описания
        description = ngo_data.description
        if description and len(description) > 1000:
            logger.debug(f"Валидация: слишком длинное описание НКО ({len(description)} символов)")
            messages += "Описание НКО слишком длинное (максимум 1000 символов)"
        
        # Проверка деятельности
        activities = ngo_data.activities
        if activities and len(activities) > 1000:
            logger.debug(f"Валидация: слишком длинное описание деятельности ({len(activities)} символов)")
            messages += "Описание деятельности НКО слишком длинное (максимум 1000 символов)"
        
        # Проверка контактов
        contact = ngo_data.contacts
        if contact and len(contact) > 500:
            logger.debug(f"Валидация: слишком длинная контактная информация ({len(contact)} символов)")
            messages += "Контактная информация слишком длинная (максимум 500 символов)"

        if messages:
            logger.debug("Валидация данных НКО не пройдена")
            return False, tuple(messages)
        
        logger.debug("Валидация данных НКО: успешно пройдена")
        return True, None

