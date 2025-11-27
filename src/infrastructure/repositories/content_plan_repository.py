"""
Репозиторий для работы с контент-планами
"""
import logging
from abc import ABCMeta, abstractmethod
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, asc

from models import ContentPlan, ContentPlanItem
from infrastructure.repositories.sqlalchemy.models.content_plan import SqlAlchemyContentPlanModel
from infrastructure.repositories.sqlalchemy.models.content_plan_item import SqlAlchemyContentPlanItemModel, PublicationStatus

logger = logging.getLogger(__name__)

class ContentPlanRepositoryException(Exception):
    pass

class ContentPlanDoesNotExists(ContentPlanRepositoryException):
    pass

class ContentPlanItemDoesNotExists(ContentPlanRepositoryException):
    pass

class AbstractContentPlanRepository(metaclass=ABCMeta):
    @abstractmethod
    def create(self, dto: ContentPlan) -> int:
        # TODO: переделать на CreateContentPlanDto
        """
        Создать новый контент-план
        """
        pass

    @abstractmethod
    def update(self, plan: ContentPlan) -> None:
        pass

    @abstractmethod
    def update_item(self, plan_item: ContentPlanItem) -> None:
        pass

    @abstractmethod
    def get_by_id(self, plan_id: int) -> ContentPlan:
        """
        Получить контент-план по ID
        """
        pass

    @abstractmethod
    def get_all_by_user_id(self, user_id: int) -> tuple[ContentPlan, ...]:
        """
        Получить все планы пользователя
        """
        pass

    @abstractmethod
    def get_content_plan_item_by_id(self, item_id: int) -> ContentPlanItem:
        """
        Получить элемент контент плана.
        """
        pass

    @abstractmethod
    def delete(self, plan_id: int) -> None:
        """
        Удалить контент-план
        """
        pass

    @abstractmethod
    def is_exists(self, plan_id: int) -> bool:
        pass

    @abstractmethod
    def get_pending_notifications(
            self,
            current_time: datetime,
            notification_window_minutes: datetime
    ) -> tuple[ContentPlanItem, ...]:
        """
        Получить элементы планов, для которых нужно отправить уведомления
        """
        pass


class SqlAlchemyContentPlanRepository(AbstractContentPlanRepository):
    """
    Репозиторий для работы с контент-планами и их элементами
    """


    def __init__(self, session: Session) -> None:
        """
        Инициализировать репозиторий с сессией базы данных
        
        Args:
            session: Сессия базы данных SQLAlchemy
        """
        self.session = session

    def _get_content_plan_entry_by_id(self, plan_id: int) -> SqlAlchemyContentPlanModel:

        content_plan: SqlAlchemyContentPlanModel | None = self.session.query(SqlAlchemyContentPlanModel).filter(
            SqlAlchemyContentPlanModel.id == plan_id
        ).first()

        if content_plan is None:
            raise ContentPlanDoesNotExists

        return content_plan

    def _get_content_plan_item_entry_by_id(self, item_id: int) -> SqlAlchemyContentPlanItemModel:
        content_plan_item: SqlAlchemyContentPlanItemModel | None = self.session.query(SqlAlchemyContentPlanItemModel).filter(
            SqlAlchemyContentPlanItemModel.id == item_id
        ).first()

        if content_plan_item is None:
            raise ContentPlanItemDoesNotExists

        return content_plan_item


    def _create_plan_entry(self, plan_dto: ContentPlan) -> SqlAlchemyContentPlanModel:
        # TODO: переработай на CreateContentPlanDto
        plan = SqlAlchemyContentPlanModel(
            user_id=plan_dto.user_id,
            plan_name=plan_dto.plan_name,
            period=plan_dto.period,
            frequency=plan_dto.frequency,
            topics=plan_dto.topics,
            details=plan_dto.details,
            plan_data=plan_dto.plan_data,
            items=[
                SqlAlchemyContentPlanItemModel(
                    content_plan_id=item.content_plan_id,
                    publication_date=item.publication_date,
                    content_title=item.content_title,
                    content_text=item.content_text,
                    status=item.status,
                    notification_sent=item.notification_sent,
                    notification_sent_at=item.notification_sent_at,
                ) for item in plan_dto.items
            ]
        )

        self.session.add(plan)
        self.session.commit()
        self.session.refresh(plan)

        return plan

    def _update_content_plan_entry(self, plan_dto: ContentPlan) -> SqlAlchemyContentPlanModel:
        plan_id = plan_dto.id_

        if plan_id is None:
            raise ValueError("ID плана None")

        plan = self._get_content_plan_entry_by_id(plan_id)

        plan.user_id = plan_dto.user_id
        plan.plan_name = plan_dto.plan_name
        plan.period = plan_dto.period
        plan.frequency = plan_dto.frequency
        plan.topics = plan_dto.topics
        plan.details = plan_dto.details
        plan.plan_data = plan_dto.plan_data
        plan.items = [SqlAlchemyContentPlanItemModel(
            id=item.id_,
            content_plan_id=item.content_plan_id,
            publication_date=item.publication_date,
            content_title=item.content_title,
            content_text=item.content_text,
            status=item.status,
            notification_sent=item.notification_sent,
            notification_sent_at=item.notification_sent_at,
        ) for item in plan_dto.items
        ]

        self.session.commit()
        self.session.refresh(plan)

        return plan

    def _update_content_plan_item_entry(self, plan_item: ContentPlanItem) -> SqlAlchemyContentPlanItemModel:
        plan_item_id = plan_item.id_

        if plan_item_id is None:
            raise ValueError("ID плана None")

        plan_item_model = self._get_content_plan_item_entry_by_id(plan_item_id)

        plan_item_model.content_plan_id = plan_item.content_plan_id
        plan_item_model.publication_date = plan_item.publication_date
        plan_item_model.content_title = plan_item.content_title
        plan_item_model.content_text = plan_item.content_text
        plan_item_model.status = plan_item.status
        plan_item_model.notification_sent = plan_item.notification_sent
        plan_item_model.notification_sent_at = plan_item.notification_sent_at

        self.session.commit()
        self.session.refresh(plan_item_model)

        return plan_item_model

    def _get_all_content_plan_entries_by_user_id(self, user_id: int) -> list[SqlAlchemyContentPlanModel]:
        query = self.session.query(SqlAlchemyContentPlanModel).filter(SqlAlchemyContentPlanModel.user_id == user_id)
        ordered_query = query.order_by(desc(SqlAlchemyContentPlanModel.created_at)).all()
        return ordered_query

    def _delete_plan_entry(self, plan_id: int) -> None:
        is_exists = self.is_exists(plan_id)
        if not is_exists:
            raise ContentPlanDoesNotExists

        self.session.query(SqlAlchemyContentPlanModel).filter(SqlAlchemyContentPlanModel.id == plan_id).delete()
        self.session.commit()

    def create(self, plan_dto: ContentPlan) -> int:
        # TODO: переработай на CreateContentPlanDto

        """
        Создать новый контент-план
        """
        if plan_dto.id_ is not None:
            raise ValueError("ID плана не None")

        plan = self._create_plan_entry(plan_dto)

        plan_id = plan.id
        logger.info(f"Создан контент-план с ID: {plan_id}")
        return plan_id

    def update(self, plan_dto: ContentPlan) -> None:
        self._update_content_plan_entry(plan_dto)

    def update_item(self, plan_item: ContentPlanItem) -> None:
        self._update_content_plan_item_entry(plan_item)

    def get_by_id(self, plan_id: int) -> ContentPlan:
        """
        Получить контент-план по ID
        """
        content_plan = self._get_content_plan_entry_by_id(plan_id)

        model = content_plan.to_domain_model()

        return model

    def get_content_plan_item_by_id(self, item_id: int) -> ContentPlanItem:
        content_plan_item = self._get_content_plan_item_entry_by_id(item_id)
        model = content_plan_item.to_domain_model()

        return model

    def get_all_by_user_id(self, user_id: int) -> tuple[ContentPlan, ...]:
        """
        Получить все планы пользователя
        """
        content_plans = self._get_all_content_plan_entries_by_user_id(user_id)

        return tuple(plan_item.to_domain_model() for plan_item in content_plans)

    def delete(self, plan_id: int) -> None:
        """
        Удалить контент-план
        """
        self._delete_plan_entry(plan_id)

    def is_exists(self, plan_id) -> bool:
        return self.session.query(SqlAlchemyContentPlanModel).filter(SqlAlchemyContentPlanModel.id == plan_id).exists()

    def get_pending_notifications(
            self,
            current_time: datetime,
            notification_window_minutes: int = 60
    ) -> tuple[ContentPlanItem, ...]:
        # TODO: м.б. переработать на без current_time?
        """
        Получить элементы планов, для которых нужно отправить уведомления
        """
        # Время, за которое нужно уведомить
        notification_time = current_time + timedelta(minutes=notification_window_minutes)

        # Ищем элементы, у которых:
        # 1. Статус SCHEDULED
        # 2. Уведомление еще не отправлено
        # 3. Время публикации попадает в окно уведомления
        items = tuple(item.to_domain_model()
                for item
                in self.session.query(
                    SqlAlchemyContentPlanItemModel
                )
                .join(
                    SqlAlchemyContentPlanModel
                )
                .filter(
                    and_(
                        SqlAlchemyContentPlanItemModel.status == PublicationStatus.SCHEDULED,
                        SqlAlchemyContentPlanItemModel.notification_sent == False,
                        SqlAlchemyContentPlanModel.is_active == True,
                        SqlAlchemyContentPlanItemModel.publication_date <= notification_time,
                        SqlAlchemyContentPlanItemModel.publication_date >= current_time
                )
            ).order_by(asc(SqlAlchemyContentPlanItemModel.publication_date)).all()
        )

        return items


