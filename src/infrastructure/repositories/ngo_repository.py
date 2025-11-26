"""
Репозиторий для работы с данными об НКО
"""
from abc import ABCMeta, abstractmethod
from sqlalchemy.orm import Session
from sqlalchemy import and_

from infrastructure.repositories.sqlalchemy.models import SqlAlchemyNgoModel
from models import Ngo


class NGORepositoryException(Exception):
    pass

class NGODoesNotExists(NGORepositoryException):
    pass

class NGOExists(NGORepositoryException):
    pass

class AbstractNGORepository(metaclass=ABCMeta):
    """
    Репозиторий для выполнения CRUD операций с данными об НКО
    """
    @abstractmethod
    def get_by_user_id(self, user_id: int) -> Ngo:
        """
        Получить НКО по ID пользователя
        """
        pass
    
    @abstractmethod
    def get_by_id(self, ngo_id: int) -> Ngo:
        """
        Получить НКО по ID записи
        """
        pass
    

    @abstractmethod
    def create(self, ngo_data: Ngo) -> None:
        """
        Создать новую запись НКО
        """
        pass
    
    @abstractmethod
    def update(self, ngo_data: Ngo) -> None:
        """
        Обновить данные об НКО
        """
        pass

    @abstractmethod
    def delete_by_id(self, ngo_id: int) -> None:
        """
        Удалить запись об НКО по ID
        """
        pass
    
    @abstractmethod
    def delete_by_user_id(self, user_id: int) -> None:
        """
        Удалить запись об НКО по ID пользователя
        """
        pass

    @abstractmethod
    def is_exists_by_id(self, id_: int) -> bool:
        """
        Проверить, существует ли запись об НКО
        """
        pass
    
    @abstractmethod
    def is_exists_by_user_id(self, user_id: int) -> bool:
        """
        Проверить, существует ли запись об НКО по пользователюы
        """
        pass


class SqlAlchemyNgoRepository(AbstractNGORepository):
    """
    Репозиторий для выполнения CRUD операций с данными об НКО
    """

    def __init__(self, session: Session):
        self.session = session


    def _get_orm_instance_by_id(self, ngo_id: int) -> SqlAlchemyNgoModel | None:
        ngo: SqlAlchemyNgoModel | None = self.session.query(SqlAlchemyNgoModel).filter(
            and_(SqlAlchemyNgoModel.id == ngo_id, SqlAlchemyNgoModel.is_active == True)
        ).first()

        if ngo is None:
            raise NGODoesNotExists
        return ngo


    def _get_orm_instance_by_user_id(self, user_id: int) -> SqlAlchemyNgoModel:
        ngo: SqlAlchemyNgoModel | None = self.session.query(SqlAlchemyNgoModel).filter(
            and_(SqlAlchemyNgoModel.user_id == user_id, SqlAlchemyNgoModel.is_active == True)
        ).first()

        if ngo is None:
            raise NGODoesNotExists

        return ngo


    def _create_ngo_entry(self, activities: str, contacts: str, description: str, ngo_name: str, user_id: int) -> SqlAlchemyNgoModel:
        # TODO: переработай на использование CreateNgoDto
        ngo = SqlAlchemyNgoModel(
            user_id=user_id,
            ngo_name=ngo_name,
            description=description,
            activities=activities,
            contacts=contacts,
        )

        self.session.add(ngo)
        self.session.commit()
        self.session.refresh(ngo)

        return ngo

    def _update_ngo_entry(self, ngo_data: Ngo) -> SqlAlchemyNgoModel:
        ngo_id = ngo_data.id_

        if ngo_id is None:
            raise ValueError("Не указан ID НКО.")

        ngo = self._get_orm_instance_by_id(ngo_id)

        ngo.user_id = ngo_data.user_id
        ngo.ngo_name = ngo_data.name
        ngo.description = ngo_data.description
        ngo.activities = ngo_data.activities
        ngo.contacts = ngo_data.contacts

        self.session.commit()
        self.session.refresh(ngo)

        return ngo

    def _delete_ngo_entry(self, ngo_id: int) -> SqlAlchemyNgoModel:
        ngo = self._get_orm_instance_by_id(ngo_id)
        ngo.is_active = False
        self.session.commit()
        self.session.refresh(ngo)
        return ngo

    def _delete_ngo_entry_by_user_id(self, user_id: int) -> SqlAlchemyNgoModel:
        ngo = self._get_orm_instance_by_user_id(user_id)
        ngo.is_active = False
        self.session.commit()
        self.session.refresh(ngo)
        return ngo

    def _is_ngo_entry_exists_by_id(self, id_: int) -> bool:
        res = self.session.query(SqlAlchemyNgoModel).filter(SqlAlchemyNgoModel.id == id_).exists()
        return res

    def is_ngo_entry_exists_by_user_id(self, user_id: int) -> bool:
        res = self.session.query((self.session.query(SqlAlchemyNgoModel).filter(SqlAlchemyNgoModel.user_id == user_id)).exists()).scalar()
        return res

    def get_by_id(self, ngo_id: int) -> Ngo:
        """
        Получить данные об НКО по ID записи
        """
        ngo = self._get_orm_instance_by_id(ngo_id)

        dto = ngo.to_domain_model()

        return dto

    def get_by_user_id(self, user_id: int) -> Ngo:
        """
        Получить данные об НКО по ID пользователя
        """
        ngo = self._get_orm_instance_by_user_id(user_id)
        model = ngo.to_domain_model()

        return model

    def create(self, ngo_data: Ngo) -> int:
        # TODO: переработай на использование CreateNgoDto

        """
        Создать новую запись об НКО
        """
        ngo_id = ngo_data.id_

        if ngo_id is not None:
            raise ValueError("ID НКО не None")


        user_id = ngo_data.user_id
        ngo_name = ngo_data.name
        description = ngo_data.description
        activities = ngo_data.activities
        contacts = ngo_data.contacts

        ngo = self._create_ngo_entry(activities, contacts, description, ngo_name, user_id)

        return ngo.id


    def update(self, ngo_data: Ngo) -> None:
        """
        Обновить данные об НКО
        """

        self._update_ngo_entry(ngo_data)

    def delete_by_id(self, ngo_id: int) -> None:
        self._delete_ngo_entry(ngo_id)

    def delete_by_user_id(self, user_id: int) -> None:
        self._delete_ngo_entry_by_user_id(user_id)

    def is_exists_by_id(self, id_: int) -> bool:
        res = self._is_ngo_entry_exists_by_id(id_)
        return res

    def is_exists_by_user_id(self, user_id: int) -> bool:
        return self.is_ngo_entry_exists_by_user_id(user_id)



    
