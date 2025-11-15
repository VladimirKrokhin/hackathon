"""
Репозиторий для работы с данными об НКО
"""
from abc import ABCMeta, abstractmethod
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from .models.ngo import NGO
from .models import Base


class AbstractNGORepository(metaclass=ABCMeta):
    """
    Репозиторий для выполнения CRUD операций с данными об НКО
    """
    @abstractmethod
    def get_by_user_id(self, user_id: int) -> Optional[NGO]:
        """
        Получить данные об НКО по ID пользователя
        """
        pass
    
    @abstractmethod
    def get_by_id(self, ngo_id: int) -> Optional[NGO]:
        """
        Получить данные об НКО по ID записи
        """
        pass
    
    @abstractmethod
    def get_all_active(self) -> List[NGO]:
        """
        Получить все активные записи об НКО
        """
        pass

    @abstractmethod
    def create(self, ngo_data: dict) -> NGO:
        """
        Создать новую запись об НКО
        """
        pass
    
    @abstractmethod
    def update(self, user_id: int, ngo_data: dict) -> Optional[NGO]:
        """
        Обновить данные об НКО для пользователя
        """
        pass
    
    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """
        "Удалить" запись об НКО (помечаем как неактивную)
        """
        pass
    
    @abstractmethod
    def exists(self, user_id: int) -> bool:
        """
        Проверить, существует ли запись об НКО для пользователя
        """
        pass

    @abstractmethod
    def get_or_create(self, user_id: int, default_data: dict = None) -> NGO:
        """
        Получить существующую запись или создать новую
        """
        pass

class NGORepository(AbstractNGORepository):
    """
    Репозиторий для выполнения CRUD операций с данными об НКО
    """
    
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_user_id(self, user_id: int) -> Optional[NGO]:
        """
        Получить данные об НКО по ID пользователя
        """
        return self.session.query(NGO).filter(
            and_(NGO.user_id == user_id, NGO.is_active == True)
        ).first()
    
    def get_by_id(self, ngo_id: int) -> Optional[NGO]:
        """
        Получить данные об НКО по ID записи
        """
        return self.session.query(NGO).filter(
            and_(NGO.id == ngo_id, NGO.is_active == True)
        ).first()
    
    def get_all_active(self) -> List[NGO]:
        """
        Получить все активные записи об НКО
        """
        return self.session.query(NGO).filter(NGO.is_active == True).all()
    
    def create(self, ngo_data: dict) -> NGO:
        """
        Создать новую запись об НКО
        """
        ngo = NGO.from_dict(ngo_data)
        self.session.add(ngo)
        self.session.commit()
        self.session.refresh(ngo)
        return ngo
    
    def update(self, user_id: int, ngo_data: dict) -> Optional[NGO]:
        """
        Обновить данные об НКО для пользователя
        """
        ngo = self.get_by_user_id(user_id)
        if not ngo:
            return None
        
        # Обновляем только переданные поля
        for field, value in ngo_data.items():
            if hasattr(ngo, field):
                setattr(ngo, field, value)
        
        self.session.commit()
        self.session.refresh(ngo)
        return ngo
    
    def delete(self, user_id: int) -> bool:
        """
        "Удалить" запись об НКО (помечаем как неактивную)
        """
        ngo = self.get_by_user_id(user_id)
        if not ngo:
            return False
        
        ngo.is_active = False
        self.session.commit()
        return True
    
    def exists(self, user_id: int) -> bool:
        """
        Проверить, существует ли запись об НКО для пользователя
        """
        ngo = self.get_by_user_id(user_id)
        return ngo is not None
    
    def get_or_create(self, user_id: int, default_data: dict = None) -> NGO:
        """
        Получить существующую запись или создать новую
        """
        ngo = self.get_by_user_id(user_id)
        if ngo:
            return ngo
        
        # Создаем новую запись с данными по умолчанию
        data = {"user_id": user_id}
        if default_data:
            data.update(default_data)
        
        return self.create(data)
