"""
Планировщик для автоматической проверки и отправки уведомлений
"""
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from services.notification_service import NotificationService
from infrastructure.database import get_db_session
from config import config

logger = logging.getLogger(__name__)


class ContentPlanScheduler:
    """
    Планировщик для проверки и отправки уведомлений о контент-планах
    """
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
        self.scheduler = None
    
    def start(self):
        """
        Запустить планировщик
        """
        try:
            if self.scheduler is not None:
                logger.warning("Планировщик уже запущен")
                return
            
            # Создаем планировщик
            self.scheduler = AsyncIOScheduler()
            
            # Добавляем задачу проверки уведомлений
            self.scheduler.add_job(
                self._check_notifications_job,
                trigger=IntervalTrigger(
                    minutes=config.NOTIFICATION_CHECK_INTERVAL
                ),
                id='check_content_plan_notifications',
                name='Проверка уведомлений контент-планов',
                replace_existing=True,
                max_instances=1,  # Только один экземпляр одновременно
                coalesce=True    # Объединять пропущенные запуски
            )
            
            # Запускаем планировщик
            self.scheduler.start()
            
            logger.info(
                f"Планировщик уведомлений контент-планов запущен. "
                f"Интервал проверки: {config.NOTIFICATION_CHECK_INTERVAL} минут"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при запуске планировщика: {e}")
            raise
    
    def stop(self):
        """
        Остановить планировщик
        """
        try:
            if self.scheduler:
                self.scheduler.shutdown(wait=False)
                self.scheduler = None
                logger.info("Планировщик уведомлений остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке планировщика: {e}")
    
    async def _check_notifications_job(self):
        """
        Фоновая задача для проверки и отправки уведомлений
        """
        try:
            logger.info("Запуск проверки уведомлений контент-планов")
            
            # Получаем сессию БД
            db = next(get_db_session())
            
            try:
                # Проверяем и отправляем уведомления
                sent_count = await self.notification_service.check_and_send_notifications(db)
                
                if sent_count > 0:
                    logger.info(f"Проверка уведомлений завершена. Отправлено: {sent_count}")
                else:
                    logger.debug("Проверка уведомлений завершена. Новых уведомлений нет")
                    
            except Exception as e:
                logger.error(f"Ошибка при проверке уведомлений в фоновой задаче: {e}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Критическая ошибка в фоновой задаче проверки уведомлений: {e}")
    
    def get_status(self) -> dict:
        """
        Получить статус планировщика
        """
        if self.scheduler is None:
            return {
                "status": "stopped",
                "running": False,
                "jobs": 0
            }
        
        try:
            jobs = self.scheduler.get_jobs()
            return {
                "status": "running" if self.scheduler.running else "stopped",
                "running": self.scheduler.running,
                "jobs": len(jobs),
                "check_interval_minutes": config.NOTIFICATION_CHECK_INTERVAL
            }
        except Exception as e:
            logger.error(f"Ошибка при получении статуса планировщика: {e}")
            return {
                "status": "error",
                "running": False,
                "jobs": 0,
                "error": str(e)
            }
