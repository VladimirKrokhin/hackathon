# Models package
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Импорты моделей
from .ngo import SqlAlchemyNgoModel
from .content_plan import SqlAlchemyContentPlanModel
from .content_plan_item import SqlAlchemyContentPlanItemModel

__all__ = ["Base", "SqlAlchemyNgoModel", "SqlAlchemyContentPlanModel", "SqlAlchemyContentPlanItemModel"]
