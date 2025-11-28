"""
Сервис для отправки уведомлений о предстоящих публикациях
"""
import logging
from datetime import datetime

from infrastructure.publication_notificator import AbstractNotificator
from models import ContentPlanItem, ContentPlan
from infrastructure.repositories.content_plan_repository import AbstractContentPlanRepository
from config import config

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Сервис для отправки уведомлений о публикациях
    """

    def __init__(
            self,
            notificator: AbstractNotificator,
            content_plan_repository: AbstractContentPlanRepository
    ) -> None:
        self.notificator: AbstractNotificator = notificator
        self.repository: AbstractContentPlanRepository = content_plan_repository



    async def _send_notification(self, item: ContentPlanItem, plan: ContentPlan) -> None:
        """
        Отправить уведомление пользователю
        """
        await self.notificator.send_notification(item, plan)

        logger.info(f"Уведомление отправлено пользователю {plan.user_id} для элемента {item.id_}")


    def _mark_as_notified(self, item_id: int) -> None:
        """
        Отправить уведомление
        """
        try:
            item = self.repository.get_content_plan_item_by_id(item_id)

            item.notification_sent = True
            item.notification_sent_at = datetime.now()
            # FIXME: !!!
            self.repository.update_item(item)
            logger.info(f"Отмечено уведомление для элемента {item_id}")
        except Exception as e:
            logger.error(f"Ошибка при отметке уведомления для элемента {item_id}: {e}")
            raise


    async def check_and_send_notifications(self) -> None:
        """
        Проверить и отправить необходимые уведомления
        """
        try:
            current_time = datetime.now()
            notification_window = config.NOTIFICATION_TIME_BEFORE

            # Получаем элементы, для которых нужно отправить уведомления
            pending_items = self.repository.get_pending_notifications(
                current_time,
                notification_window_minutes=notification_window
            )

        except Exception as e:
            logger.error(f"Ошибка при получении уведомлений: {e}")
            raise


        for item in pending_items:
            try:
                # Получаем план для этого элемента
                plan = self.repository.get_by_id(item.content_plan_id)
                # Отправляем уведомление
                await self._send_notification(item, plan)
                self._mark_as_notified(item.id_)

            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления для элемента {item.id_}: {e}")
                raise

