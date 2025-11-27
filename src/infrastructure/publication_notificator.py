import logging
from abc import ABCMeta, abstractmethod

from aiogram import Bot
from aiogram.enums import ParseMode

from models import ContentPlanItem, ContentPlan

logger = logging.getLogger(__name__)

class AbstractNotificator(metaclass=ABCMeta):
    @abstractmethod
    async def send_notification(
            self,
            item: ContentPlanItem,
            plan: ContentPlan
    ) -> None:
        """Отправить уведомление."""
        pass


class TelegramBotNotificator(AbstractNotificator):
    def __init__(self, bot: Bot):
        self.bot = bot

    @staticmethod
    def _format_notification_message(item: ContentPlanItem, plan: ContentPlan) -> str:
        """
        Форматировать сообщение уведомления
        """
        try:
            # Форматируем дату и время публикации
            pub_date = item.publication_date
            date_str = pub_date.strftime("%d.%m.%Y")
            time_str = pub_date.strftime("%H:%M")

            # Формируем сообщение
            message = (
                f"🔔 *Через час нужно опубликовать:*\n\n"
                f"📋 *{item.content_title}*\n"
                f"📅 *Дата:* {date_str} в {time_str}\n"
                f"📊 *План:* {plan.plan_name}\n"
                f"💡 *Не забудьте подготовить материал для публикации!*"
            )

            return message

        except Exception as e:
            logger.error(f"Ошибка при форматировании уведомления: {e}")
            raise

    async def send_notification(
            self,
            item: ContentPlanItem,
            plan: ContentPlan
    ) -> None:
        # Форматируем сообщение
        message = self._format_notification_message(item, plan)

        # Отправляем сообщение пользователю
        await self.bot.send_message(
            chat_id=plan.user_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )