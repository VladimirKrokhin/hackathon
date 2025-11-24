"""
Модуль шины событий для управления жизненным циклом сервисов.

Предоставляет централизованный механизм для регистрации и выполнения
функций startup и shutdown при инициализации и остановке приложения.
"""

import logging
from typing import Callable, Awaitable, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class ServiceBus:
    """
    Шина событий для управления жизненным циклом сервисов.
    
    Позволяет сервисам регистрировать функции, которые должны выполняться
    при старте и остановке приложения, обеспечивая децентрализованное
    управление lifecycle.
    """
    
    def __init__(self):
        """Инициализация шины событий."""
        self._startup_functions: List[Callable] = []
        self._shutdown_functions: List[Callable] = []
        logger.info("ServiceBus инициализирован")
    
    def register_startup(self, func: Callable) -> None:
        """
        Регистрация функции для выполнения при старте приложения.
        
        Args:
            func (Callable): Асинхронная функция без параметров
        """
        if func not in self._startup_functions:
            self._startup_functions.append(func)
            logger.debug(f"Зарегистрирована startup функция: {func.__name__}")
    
    def register_shutdown(self, func: Callable) -> None:
        """
        Регистрация функции для выполнения при остановке приложения.
        
        Args:
            func (Callable): Асинхронная функция без параметров
        """
        if func not in self._shutdown_functions:
            self._shutdown_functions.append(func)
            logger.debug(f"Зарегистрирована shutdown функция: {func.__name__}")
    
    async def execute_startup(self) -> None:
        """
        Выполнение всех зарегистрированных startup функций.
        
        Выполняется последовательно в порядке регистрации.
        """
        logger.info("Начинаю выполнение startup функций")
        for i, func in enumerate(self._startup_functions, 1):
            try:
                logger.info(f"Выполняю startup функцию {i}/{len(self._startup_functions)}: {func.__name__}")
                if func.__code__.co_argcount == 0:
                    # Функция без параметров
                    if hasattr(func, '__await__'):
                        await func()
                    else:
                        func()
                else:
                    # Функция с параметрами - попробуем передать bot, dispatcher если есть
                    logger.warning(f"Функция {func.__name__} имеет параметры, но ServiceBus ожидает функции без параметров")
                    await func()
            except Exception as e:
                logger.error(f"Ошибка при выполнении startup функции {func.__name__}: {e}")
                raise
        logger.info("Все startup функции выполнены")
    
    async def execute_shutdown(self) -> None:
        """
        Выполнение всех зарегистрированных shutdown функций.
        
        Выполняется в обратном порядке для корректного завершения зависимостей.
        """
        logger.info("Начинаю выполнение shutdown функций")
        shutdown_functions = list(reversed(self._shutdown_functions))
        
        for i, func in enumerate(shutdown_functions, 1):
            try:
                logger.info(f"Выполняю shutdown функцию {i}/{len(shutdown_functions)}: {func.__name__}")
                if func.__code__.co_argcount == 0:
                    # Функция без параметров
                    if hasattr(func, '__await__'):
                        await func()
                    else:
                        func()
                else:
                    # Функция с параметрами
                    logger.warning(f"Функция {func.__name__} имеет параметры, но ServiceBus ожидает функции без параметров")
                    await func()
            except Exception as e:
                logger.error(f"Ошибка при выполнении shutdown функции {func.__name__}: {e}")
                # Не прерываем выполнение других shutdown функций при ошибке
                continue
        logger.info("Все shutdown функции выполнены")
    
    def get_startup_count(self) -> int:
        """Получить количество зарегистрированных startup функций."""
        return len(self._startup_functions)
    
    def get_shutdown_count(self) -> int:
        """Получить количество зарегистрированных shutdown функций."""
        return len(self._shutdown_functions)
    
    def get_registered_functions(self) -> dict:
        """
        Получить информацию о зарегистрированных функциях.
        
        Returns:
            dict: Информация о startup и shutdown функциях
        """
        return {
            "startup": [func.__name__ for func in self._startup_functions],
            "shutdown": [func.__name__ for func in self._shutdown_functions]
        }


# Глобальный экземпляр ServiceBus
service_bus = ServiceBus()
