"""
Модель данных для НКО (Non-Governmental Organization)
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func

from models import Ngo
from . import Base


class SqlAlchemyNgoModel(Base):
    """
    Модель для хранения информации об НКО пользователей
    """
    __tablename__ = "ngos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True, nullable=False, comment="ID пользователя Telegram")
    
    # Основная информация об НКО
    ngo_name = Column(String(255), nullable=False, comment="Название НКО")
    description = Column(Text, nullable=True, comment="Описание деятельности НКО")
    activities = Column(Text, nullable=True, comment="Формы деятельности НКО")
    contacts = Column(Text, nullable=True, comment="Контактная информация")
    
    # Метаданные
    is_active = Column(Boolean, default=True, comment="Активна ли запись")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="Дата создания")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="Дата обновления")
    
    def to_domain_model(self) -> Ngo:
        """Преобразование модели в DTO."""
        dto = Ngo(
            id_=self.id,
            user_id=self.user_id,
            name=self.ngo_name,
            description=self.description,
            activities=self.activities,
            contacts=self.contacts
        )

        return dto

    @classmethod
    def from_domain_model(cls, dto: Ngo) -> "SqlAlchemyNgoModel":
        ngo = cls(
            id=dto.id_,
            user_id=dto.user_id,
            ngo_name=dto.name,
            description=dto.description,
            activities=dto.activities,
            contacts=dto.contacts,
        )

        return ngo



