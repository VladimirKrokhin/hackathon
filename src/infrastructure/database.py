"""
Конфигурация базы данных
"""
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from infrastructure.repositories.models import Base
from infrastructure.repositories.models.ngo import NGO

logger = logging.getLogger(__name__)


class Database:
    """
    Класс для управления подключением к базе данных
    """
    
    def __init__(self, database_url: str = "sqlite:///./ngo_data.db"):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def init_db(self):
        """
        Инициализация базы данных
        """
        try:
            # Создаем движок базы данных
            self.engine = create_engine(
                self.database_url,
                poolclass=StaticPool,
                connect_args={"check_same_thread": False}  # Для SQLite
            )
            
            # Создаем фабрику сессий
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Создаем таблицы
            Base.metadata.create_all(bind=self.engine)
            
            logger.info("База данных успешно инициализирована")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации базы данных: {e}")
            raise
    
    def get_session(self) -> Session:
        """
        Получить сессию базы данных
        """
        if not self.SessionLocal:
            raise RuntimeError("База данных не инициализирована. Вызовите init_db()")
        
        db = self.SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def close(self):
        """
        Закрыть соединение с базой данных
        """
        if self.engine:
            self.engine.dispose()
            logger.info("Соединение с базой данных закрыто")


# Глобальный экземпляр базы данных
db = Database()


def get_db_session() -> Session:
    """
    Получить сессию базы данных для использования в репозиториях
    """
    return db.SessionLocal()


def init_database():
    """
    Инициализация базы данных
    """
    db.init_db()
