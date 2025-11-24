"""
Сервис для отправки уведомлений о предстоящих публикациях
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from aiogram import Bot
from aiogram.enums import ParseMode

from infrastructure.repositories.models.content_plan_item import ContentPlanItem
from infrastructure.repositories.content_plan_repository import ContentPlanRepository
from infrastructure.repositories.models.content_plan import ContentPlan
from config import config

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Сервис для отправки уведомлений о публикациях
    """
    
    def __init__(self, bot: Bot, content_plan_repository: ContentPlanRepository):
        self.bot = bot
        self.repository = content_plan_repository
    
    def format_notification_message(self, item: ContentPlanItem, plan: ContentPlan) -> str:
        """
        Форматировать сообщение уведомления
        """
        try:
            # Форматируем дату и время публикации
            pub_date = item.publication_date
            date_str = pub_date.strftime("%d.%m.%Y")
            time_str = pub_date.strftime("%H:%M")
            
            # Определяем статус плана
            status_emoji = "✅" if plan.is_active else "⏸️"
            status_text = "Активен" if plan.is_active else "Приостановлен"
            
            # Формируем сообщение
            message = f"🔔 *Через час нужно опубликовать:*\n\n"
            message += f"📋 *{item.content_title}*\n"
            message += f"📅 *Дата:* {date_str} в {time_str}\n"
            message += f"📊 *План:* {plan.plan_name} ({status_emoji} {status_text})\n"
            message += f"🆔 *ID плана:* `{plan.id}`\n\n"
            message += f"💡 *Не забудьте подготовить материал для публикации!*"
            
            return message
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании уведомления: {e}")
            return "🔔 Напоминание о предстоящей публикации!"
    
    async def send_notification(self, item: ContentPlanItem, plan: ContentPlan) -> bool:
        """
        Отправить уведомление пользователю
        """
        try:
            # Форматируем сообщение
            message = self.format_notification_message(item, plan)
            
            # Отправляем сообщение пользователю
            await self.bot.send_message(
                chat_id=plan.user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Уведомление отправлено пользователю {plan.user_id} для элемента {item.id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {plan.user_id}: {e}")
            return False
    
    async def check_and_send_notifications(self) -> int:
        """
        Проверить и отправить необходимые уведомления
        
        Returns:
            Количество отправленных уведомлений
        """
        try:
            current_time = datetime.now()
            notification_window = config.NOTIFICATION_TIME_BEFORE
            
            # Получаем элементы, для которых нужно отправить уведомления
            pending_items = self.repository.get_pending_notifications(
                current_time, 
                notification_window_minutes=notification_window
            )
            
            sent_count = 0
            
            for item in pending_items:
                try:
                    # Получаем план для этого элемента
                    plan = self.repository._db.query(ContentPlan).filter(
                        ContentPlan.id == item.content_plan_id
                    ).first()
                    
                    if plan and plan.is_active:
                        # Отправляем уведомление
                        success = await self.send_notification(item, plan)
                        
                        if success:
                            # Отмечаем, что уведомление отправлено
                            self.repository.mark_notification_sent(item.id)
                            sent_count += 1
                            
                except Exception as e:
                    logger.error(f"Ошибка при обработке уведомления для элемента {item.id}: {e}")
                    continue
            
            if sent_count > 0:
                logger.info(f"Отправлено {sent_count} уведомлений")
            
            return sent_count
            
        except Exception as e:
            logger.error(f"Ошибка при проверке уведомлений: {e}")
            return 0
    
    async def send_plan_created_notification(self, plan: ContentPlan, item_count: int) -> bool:
        """
        Отправить уведомление о создании нового плана
        """
        try:
            message = f"✅ *Контент-план создан!*\n\n"
            message += f"📋 *Название:* {plan.plan_name}\n"
            message += f"📅 *Период:* {plan.period}\n"
            message += f"🔁 *Частота:* {plan.frequency}\n"
            message += f"📝 *Темы:* {plan.themes}\n"
            message += f"📊 *Создано публикаций:* {item_count}\n"
            message += f"🆔 *ID плана:* `{plan.id}`\n\n"
            message += f"💡 *Вы будете получать уведомления за час до каждой публикации.*"
            
            await self.bot.send_message(
                chat_id=plan.user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Уведомление о создании плана отправлено пользователю {plan.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о создании плана: {e}")
            return False
    
    async def send_plan_status_notification(self, plan: ContentPlan, action: str) -> bool:
        """
        Отправить уведомление об изменении статуса плана
        """
        try:
            status_text = "активирован" if plan.is_active else "приостановлен"
            status_emoji = "✅" if plan.is_active else "⏸️"
            
            message = f"{status_emoji} *Контент-план {status_text}*\n\n"
            message += f"📋 *Название:* {plan.plan_name}\n"
            message += f"🆔 *ID плана:* `{plan.id}`"
            
            if plan.is_active:
                message += f"\n\n💡 *Уведомления о публикациях возобновлены.*"
            else:
                message += f"\n\n💡 *Уведомления о публикациях приостановлены.*"
            
            await self.bot.send_message(
                chat_id=plan.user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Уведомление об изменении статуса плана отправлено пользователю {plan.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об изменении статуса: {e}")
            return False
    
    async def send_plan_deleted_notification(self, plan: ContentPlan) -> bool:
        """
        Отправить уведомление об удалении плана
        """
        try:
            message = f"🗑️ *Контент-план удален*\n\n"
            message += f"📋 *Название:* {plan.plan_name}\n"
            message += f"🆔 *ID плана:* `{plan.id}`\n\n"
            message += f"💡 *Все уведомления по этому плану отключены.*"
            
            await self.bot.send_message(
                chat_id=plan.user_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Уведомление об удалении плана отправлено пользователю {plan.user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об удалении: {e}")
            return False
