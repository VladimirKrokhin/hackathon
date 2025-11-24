"""
Сервис для управления контент-планами
"""
import logging
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from infrastructure.repositories.content_plan_repository import ContentPlanRepository
from infrastructure.repositories.models.content_plan import ContentPlan
from infrastructure.repositories.models.content_plan_item import ContentPlanItem, PublicationStatus
from infrastructure.database import get_db_session

logger = logging.getLogger(__name__)


class ContentPlanService:
    """
    Сервис для работы с контент-планами
    """
    
    def __init__(self, content_plan_repository: ContentPlanRepository):
        self.repository = content_plan_repository
    
    async def save_content_plan(
        self, 
        user_id: int, 
        user_data: Dict[str, Any], 
        generated_plan: str
    ) -> int:
        """
        Сохранить контент-план в базу данных
        
        Args:
            user_id: ID пользователя
            user_data: Данные пользователя (period, frequency, themes, details)
            generated_plan: Сгенерированный текст плана
        
        Returns:
            ID созданного плана
        """
        try:
            # Создаем название плана на основе данных
            plan_name = f"План на {user_data.get('period', 'неизвестный период')}"
            
            plan_data = {
                "user_id": user_id,
                "plan_name": plan_name,
                "period": user_data.get("period"),
                "frequency": user_data.get("frequency"),
                "themes": user_data.get("themes"),
                "details": user_data.get("details"),
                "plan_data": {"generated_plan": generated_plan, "raw_data": user_data},
                "is_active": True
            }
            
            plan = self.repository.create_plan(plan_data)
            
            # Генерируем расписание публикаций
            await self._generate_schedule(plan.id, generated_plan)
            
            logger.info(f"Контент-план {plan.id} сохранен для пользователя {user_id}")
            return plan.id
            
        except Exception as e:
            logger.error(f"Ошибка при сохранении контент-плана: {e}")
            raise
    
    async def _generate_schedule(self, plan_id: int, generated_plan: str) -> None:
        """
        Генерировать расписание публикаций на основе сгенерированного плана
        """
        try:
            # Парсим сгенерированный план для извлечения дат и тем
            schedule_items = self._parse_plan_schedule(generated_plan)
            
            if schedule_items:
                # Создаем элементы плана
                for item_data in schedule_items:
                    # Добавляем plan_id к данным элемента
                    item_data['content_plan_id'] = plan_id
                    self.repository.create_plan_item(item_data)
                    
                logger.info(f"Создано {len(schedule_items)} элементов для плана {plan_id}")
            else:
                logger.warning(f"Не удалось распарсить расписание для плана {plan_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при генерации расписания для плана {plan_id}: {e}")
    
    def _parse_plan_schedule(self, generated_plan: str) -> List[Dict[str, Any]]:
        """
        Парсить сгенерированный план и извлечь элементы расписания
        """
        items = []
        
        try:
            # Ищем паттерны дат и тем в тексте
            # Примеры форматов:
            # "25.11 - Тема поста"
            # "26 ноября - Другая тема"
            # "27.11.2024 - Еще одна тема"
            
            date_patterns = [
                r'(\d{1,2}[./]\d{1,2}(?:[./]\d{4})?)\s*[-–—]\s*(.+)',
                r'(\d{1,2}\s+\w+\s+\d{4})\s*[-–—]\s*(.+)',
                r'(\d{1,2}\s+\w+)\s*[-–—]\s*(.+)',
            ]
            
            for pattern in date_patterns:
                matches = re.finditer(pattern, generated_plan, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    date_str = match.group(1).strip()
                    title = match.group(2).strip()
                    
                    # Парсим дату
                    try:
                        pub_date = self._parse_date(date_str)
                        if pub_date and pub_date > datetime.now():
                            items.append({
                                "publication_date": pub_date,
                                "content_title": title[:255],  # Ограничение по длине
                                "content_text": f"Запланированная публикация: {title}",
                                "status": PublicationStatus.SCHEDULED,
                                "notification_sent": False
                            })
                    except Exception as e:
                        logger.warning(f"Не удалось распарсить дату '{date_str}': {e}")
                        continue
            
            # Если не нашли даты в тексте, создаем расписание автоматически
            if not items:
                items = self._generate_auto_schedule(generated_plan)
                
        except Exception as e:
            logger.error(f"Ошибка при парсинге расписания: {e}")
            # В случае ошибки создаем базовое расписание
            items = self._generate_auto_schedule(generated_plan)
        
        return items
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Парсить строку даты в объект datetime
        """
        try:
            # Убираем лишние символы
            date_str = date_str.strip()
            
            # Форматы для парсинга
            formats = [
                '%d.%m.%Y',
                '%d.%m',
                '%d/%m/%Y',
                '%d/%m',
                '%d %B %Y',
                '%d %b %Y',
                '%d %B',
                '%d %b'
            ]
            
            current_year = datetime.now().year
            
            for fmt in formats:
                try:
                    if 'Y' not in fmt:
                        # Если год не указан, используем текущий
                        date_str_with_year = f"{date_str}.{current_year}"
                        fmt_with_year = fmt + '.%Y'
                        return datetime.strptime(date_str_with_year, fmt_with_year)
                    else:
                        return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Не удалось распарсить дату '{date_str}': {e}")
            return None
    
    def _generate_auto_schedule(self, generated_plan: str) -> List[Dict[str, Any]]:
        """
        Генерировать автоматическое расписание, если не удалось распарсить даты
        """
        items = []
        
        try:
            # Извлекаем примерные темы из плана
            lines = generated_plan.split('\n')
            topics = []
            
            for line in lines:
                line = line.strip()
                # Ищем строки, которые могут быть темами постов
                if any(keyword in line.lower() for keyword in ['пост', 'статья', 'новост', 'истор', 'совет', 'событ']):
                    # Убираем номера и символы в начале
                    clean_line = re.sub(r'^[\d\.\-\*\•\s]+', '', line).strip()
                    if clean_line and len(clean_line) > 10:
                        topics.append(clean_line[:100])
            
            # Если тем не нашли, создаем общие
            if not topics:
                topics = [
                    "Обновление о деятельности фонда",
                    "История успеха",
                    "Полезные советы",
                    "Анонс мероприятия"
                ]
            
            # Генерируем расписание на ближайшие дни
            start_date = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)
            
            for i, topic in enumerate(topics[:5]):  # Максимум 5 постов
                pub_date = start_date + timedelta(days=i)
                items.append({
                    "publication_date": pub_date,
                    "content_title": topic,
                    "content_text": f"Запланированная публикация: {topic}",
                    "status": PublicationStatus.SCHEDULED,
                    "notification_sent": False
                })
            
        except Exception as e:
            logger.error(f"Ошибка при автогенерации расписания: {e}")
            
        return items
    
    async def get_user_plans(self, user_id: int) -> List[ContentPlan]:
        """
        Получить все планы пользователя
        """
        try:
            plans = self.repository.get_user_plans(user_id, active_only=False)
            return plans
        except Exception as e:
            logger.error(f"Ошибка при получении планов пользователя {user_id}: {e}")
            return []
    
    async def get_plan_details(self, plan_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить детальную информацию о плане с элементами
        """
        try:
            plan = self.repository.get_plan_by_id(plan_id, user_id)
            if not plan:
                return None
            
            items = self.repository.get_plan_items(plan_id, user_id)
            
            return {
                "plan": plan.to_dict(),
                "items": [item.to_dict() for item in items]
            }
        except Exception as e:
            logger.error(f"Ошибка при получении деталей плана {plan_id}: {e}")
            return None
    
    async def pause_plan(self, plan_id: int, user_id: int) -> bool:
        """
        Приостановить план
        """
        try:
            success = self.repository.update_plan_status(plan_id, user_id, False)
            return success
        except Exception as e:
            logger.error(f"Ошибка при приостановке плана {plan_id}: {e}")
            return False
    
    async def resume_plan(self, plan_id: int, user_id: int) -> bool:
        """
        Возобновить план
        """
        try:
            success = self.repository.update_plan_status(plan_id, user_id, True)
            return success
        except Exception as e:
            logger.error(f"Ошибка при возобновлении плана {plan_id}: {e}")
            return False
    
    async def delete_plan(self, plan_id: int, user_id: int) -> bool:
        """
        Удалить план (мягкое удаление)
        """
        try:
            success = self.repository.delete_plan(plan_id, user_id)
            return success
        except Exception as e:
            logger.error(f"Ошибка при удалении плана {plan_id}: {e}")
            return False
    
    async def mark_item_published(self, item_id: int) -> bool:
        """
        Отметить элемент как опубликованный
        """
        try:
            success = self.repository.update_item_status(item_id, PublicationStatus.PUBLISHED)
            return success
        except Exception as e:
            logger.error(f"Ошибка при отметке элемента {item_id} как опубликованного: {e}")
            return False
