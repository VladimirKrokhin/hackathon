"""
Сервис для работы с данными об НКО
"""
from typing import Optional, Dict, Any
import logging

from infrastructure.repositories.ngo_repository import AbstractNGORepository

logger = logging.getLogger(__name__)


class NGOService:
    """
    Сервис для бизнес-логики работы с данными об НКО
    """
    
    def __init__(self, repository: AbstractNGORepository):
        self.repository = repository
    
    def get_ngo_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить данные об НКО пользователя
        """
        try:
            ngo = self.repository.get_by_user_id(user_id)
            if ngo:
                return {
                    "has_ngo_info": True,
                    "ngo_name": ngo.ngo_name,
                    "ngo_description": ngo.description or "Не указано",
                    "ngo_activities": ngo.activities or "Не указано",
                    "ngo_contact": ngo.contact or "Не указано",
                }
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении данных НКО для пользователя {user_id}: {e}")
            return None
    
    def create_or_update_ngo(self, user_id: int, ngo_data: Dict[str, Any]) -> bool:
        """
        Создать или обновить данные об НКО
        """
        try:
            # Валидация обязательных полей
            if not ngo_data.get("ngo_name", "").strip():
                raise ValueError("Название НКО не может быть пустым")
            
            # Подготавливаем данные для сохранения
            data_to_save = {
                "user_id": user_id,
                "ngo_name": ngo_data.get("ngo_name", "").strip(),
                "description": ngo_data.get("description") or "Не указано",
                "activities": ngo_data.get("activities") or "Не указано",
                "contact": ngo_data.get("contact") or "Не указано",
            }
            
            # Проверяем, существует ли запись
            if self.repository.exists(user_id):
                # Обновляем существующую запись
                updated_ngo = self.repository.update(user_id, data_to_save)
                if updated_ngo:
                    logger.info(f"Обновлены данные НКО для пользователя {user_id}")
                    return True
                else:
                    logger.error(f"Не удалось обновить данные НКО для пользователя {user_id}")
                    return False
            else:
                # Создаем новую запись
                new_ngo = self.repository.create(data_to_save)
                if new_ngo:
                    logger.info(f"Созданы данные НКО для пользователя {user_id}")
                    return True
                else:
                    logger.error(f"Не удалось создать данные НКО для пользователя {user_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных НКО для пользователя {user_id}: {e}")
            return False
    
    def delete_ngo(self, user_id: int) -> bool:
        """
        Удалить данные об НКО пользователя
        """
        try:
            success = self.repository.delete(user_id)
            if success:
                logger.info(f"Удалены данные НКО для пользователя {user_id}")
            else:
                logger.warning(f"Не найдены данные НКО для удаления для пользователя {user_id}")
            return success
        except Exception as e:
            logger.error(f"Ошибка при удалении данных НКО для пользователя {user_id}: {e}")
            return False
    
    def ngo_exists(self, user_id: int) -> bool:
        """
        Проверить, существуют ли данные об НКО для пользователя
        """
        try:
            return self.repository.exists(user_id)
        except Exception as e:
            logger.error(f"Ошибка при проверке существования данных НКО для пользователя {user_id}: {e}")
            return False
    
    def get_ngo_summary(self, user_id: int) -> Optional[str]:
        """
        Получить краткую сводку данных об НКО для отображения пользователю
        """
        try:
            ngo = self.repository.get_by_user_id(user_id)
            if not ngo:
                return None
            
            summary = (
                f"🏢 **Информация о НКО \"{ngo.ngo_name}\"**\n\n"
                f"📝 **Описание:** {ngo.description or 'Не указано'}\n\n"
                f"🎯 **Деятельность:** {ngo.activities or 'Не указано'}\n\n"
                f"📞 **Контакты:** {ngo.contact or 'Не указано'}\n\n"
            )
            return summary
        except Exception as e:
            logger.error(f"Ошибка при получении сводки НКО для пользователя {user_id}: {e}")
            return None
    
    def validate_ngo_data(self, ngo_data: Dict[str, Any]) -> tuple[bool, str]:
        """
        Валидация данных об НКО
        """
        # Проверка обязательного поля
        if not ngo_data.get("ngo_name", "").strip():
            return False, "Название НКО обязательно для заполнения"
        
        # Проверка длины названия
        if len(ngo_data.get("ngo_name", "").strip()) > 255:
            return False, "Название НКО слишком длинное (максимум 255 символов)"
        
        # Проверка описания
        description = ngo_data.get("description", "")
        if description and len(description) > 1000:
            return False, "Описание НКО слишком длинное (максимум 1000 символов)"
        
        # Проверка деятельности
        activities = ngo_data.get("activities", "")
        if activities and len(activities) > 1000:
            return False, "Описание деятельности НКО слишком длинное (максимум 1000 символов)"
        
        # Проверка контактов
        contact = ngo_data.get("contact", "")
        if contact and len(contact) > 500:
            return False, "Контактная информация слишком длинная (максимум 500 символов)"
        
        return True, "Данные корректны"
