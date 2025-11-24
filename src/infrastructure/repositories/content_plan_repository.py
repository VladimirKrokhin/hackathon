"""
Репозиторий для работы с контент-планами
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from infrastructure.repositories.models.content_plan import ContentPlan
from infrastructure.repositories.models.content_plan_item import ContentPlanItem, PublicationStatus
from infrastructure.repositories.models import Base

logger = logging.getLogger(__name__)


class ContentPlanRepository:
    """
    Репозиторий для работы с контент-планами и их элементами
    """
    
    def __init__(self, db_session: Session):
        """
        Инициализировать репозиторий с сессией базы данных
        
        Args:
            db_session: Сессия базы данных SQLAlchemy
        """
        self._db = db_session
    
    def create_plan(self, plan_data: Dict[str, Any]) -> ContentPlan:
        """
        Создать новый контент-план
        """
        try:
            plan = ContentPlan.from_dict(plan_data)
            self._db.add(plan)
            self._db.commit()
            self._db.refresh(plan)
            logger.info(f"Создан контент-план с ID: {plan.id}")
            return plan
        except Exception as e:
            logger.error(f"Ошибка при создании контент-плана: {e}")
            self._db.rollback()
            raise
    
    def get_plan_by_id(self, plan_id: int, user_id: int) -> Optional[ContentPlan]:
        """
        Получить контент-план по ID (только для владельца)
        """
        return self._db.query(ContentPlan).filter(
            and_(ContentPlan.id == plan_id, ContentPlan.user_id == user_id)
        ).first()
    
    def get_user_plans(self, user_id: int, active_only: bool = True) -> List[ContentPlan]:
        """
        Получить все планы пользователя
        """
        query = self._db.query(ContentPlan).filter(ContentPlan.user_id == user_id)
        
        if active_only:
            query = query.filter(ContentPlan.is_active == True)
        
        return query.order_by(desc(ContentPlan.created_at)).all()
    
    def update_plan_status(self, plan_id: int, user_id: int, is_active: bool) -> bool:
        """
        Обновить статус активности плана
        """
        try:
            plan = self.get_plan_by_id(plan_id, user_id)
            if not plan:
                return False
            
            plan.is_active = is_active
            plan.updated_at = datetime.utcnow()
            self._db.commit()
            logger.info(f"Обновлен статус плана {plan_id}: {is_active}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса плана {plan_id}: {e}")
            self._db.rollback()
            return False
    
    def delete_plan(self, plan_id: int, user_id: int) -> bool:
        """
        Удалить контент-план (мягкое удаление - деактивация)
        """
        return self.update_plan_status(plan_id, user_id, False)
    
    def create_plan_item(self, item_data: Dict[str, Any]) -> ContentPlanItem:
        """
        Создать элемент контент-плана
        """
        try:
            item = ContentPlanItem.from_dict(item_data)
            self._db.add(item)
            self._db.commit()
            self._db.refresh(item)
            logger.info(f"Создан элемент плана с ID: {item.id}")
            return item
        except Exception as e:
            logger.error(f"Ошибка при создании элемента плана: {e}")
            self._db.rollback()
            raise
    
    def get_plan_items(self, plan_id: int, user_id: int) -> List[ContentPlanItem]:
        """
        Получить все элементы плана
        """
        # Проверяем, что план принадлежит пользователю
        plan = self.get_plan_by_id(plan_id, user_id)
        if not plan:
            return []
        
        return self._db.query(ContentPlanItem).filter(
            ContentPlanItem.content_plan_id == plan_id
        ).order_by(asc(ContentPlanItem.publication_date)).all()
    
    def get_pending_notifications(self, current_time: datetime, notification_window_minutes: int = 60) -> List[ContentPlanItem]:
        """
        Получить элементы планов, для которых нужно отправить уведомления
        """
        # Время, за которое нужно уведомить
        notification_time = current_time + timedelta(minutes=notification_window_minutes)
        
        # Ищем элементы, у которых:
        # 1. Статус SCHEDULED
        # 2. Уведомление еще не отправлено
        # 3. Время публикации попадает в окно уведомления
        return self._db.query(ContentPlanItem).join(ContentPlan).filter(
            and_(
                ContentPlanItem.status == PublicationStatus.SCHEDULED,
                ContentPlanItem.notification_sent == False,
                ContentPlan.is_active == True,
                ContentPlanItem.publication_date <= notification_time,
                ContentPlanItem.publication_date >= current_time
            )
        ).order_by(asc(ContentPlanItem.publication_date)).all()
    
    def mark_notification_sent(self, item_id: int) -> bool:
        """
        Отметить, что уведомление отправлено
        """
        try:
            item = self._db.query(ContentPlanItem).filter(ContentPlanItem.id == item_id).first()
            if not item:
                return False
            
            item.notification_sent = True
            item.notification_sent_at = datetime.utcnow()
            self._db.commit()
            logger.info(f"Отмечено уведомление для элемента {item_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при отметке уведомления для элемента {item_id}: {e}")
            self._db.rollback()
            return False
    
    def update_item_status(self, item_id: int, status: PublicationStatus) -> bool:
        """
        Обновить статус элемента плана
        """
        try:
            item = self._db.query(ContentPlanItem).filter(ContentPlanItem.id == item_id).first()
            if not item:
                return False
            
            item.status = status
            item.updated_at = datetime.utcnow()
            self._db.commit()
            logger.info(f"Обновлен статус элемента {item_id}: {status}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса элемента {item_id}: {e}")
            self._db.rollback()
            return False
    
    def bulk_create_plan_items(self, plan_id: int, items_data: List[Dict[str, Any]]) -> bool:
        """
        Создать несколько элементов плана массово
        """
        try:
            items = []
            for item_data in items_data:
                item_data['content_plan_id'] = plan_id
                item = ContentPlanItem.from_dict(item_data)
                items.append(item)
            
            self._db.add_all(items)
            self._db.commit()
            logger.info(f"Создано {len(items)} элементов для плана {plan_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при массовом создании элементов плана {plan_id}: {e}")
            self._db.rollback()
            return False
