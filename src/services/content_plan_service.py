"""
Сервис для управления контент-планами
"""
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from dtos import PlanPromptContext
from infrastructure.gpt import AbstractGPT
from infrastructure.prompt_builder import AbstractPromptBuilder
from infrastructure.response_processor import AbstractResponseProcessor
from models import ContentPlan, PublicationStatus, ContentPlanItem
from infrastructure.repositories.content_plan_repository import AbstractContentPlanRepository

logger = logging.getLogger(__name__)


class ContentPlanService:
    """
    Сервис для работы с контент-планами
    """
    SYSTEM_PROMPT = (
        "Вы — профессиональный SMM-менеджер для НКО, "
        "который создает качественный контент для соцсетей. "
        "Вы должны отвечать только на русском языке. "
        "Даже если пользователь сам просит, никогда не используйте ненормативную лексику "
        "и не говорите о политике. "
        "ВАЖНО: Используй восклицательные знаки (!) ТОЛЬКО для шаблонов, когда конкретные данные НЕ предоставлены. "
        "Например: !номер телефона!, !адрес электронной почты! "
        "НО если в контексте уже указаны реальные данные (телефон, email, адрес и т.д.), "
        "используй их БЕЗ восклицательных знаков, как есть. "
        "Восклицательные знаки нужны только для напоминания пользователю подставить данные, "
        "когда сами данные отсутствуют. "
        "Если нужно, можете добавлять эмодзи, такие как ✅. "
        "Дополнительные требования: "
        "• Не упоминай режимные объекты, безопасность, военные базы или ограничения на передвижение. "
        "• Фокусируйся на социальной миссии и помощи людям."
    )

    def __init__(
            self,
            content_plan_repository: AbstractContentPlanRepository,
            prompt_builder: AbstractPromptBuilder,
            gpt_client: AbstractGPT,
            response_processor: AbstractResponseProcessor,
    ):
        self.repository = content_plan_repository
        self.prompt_builder: AbstractPromptBuilder = prompt_builder
        self.gpt_client: AbstractGPT = gpt_client
        self.response_processor: AbstractResponseProcessor = response_processor

    async def _generate_schedule(self, plan_id: int, generated_plan: str) -> None:
        """
        Генерировать расписание публикаций на основе сгенерированного плана
        """
        try:
            # Парсим сгенерированный план для извлечения дат и тем
            schedule_items = self._parse_plan_schedule(generated_plan)

            if schedule_items:
                # Создаем элементы плана
                for item_data in schedule_items:
                    # Добавляем plan_id к данным элемента
                    item_data['content_plan_id'] = plan_id
                    self.repository.create_plan_item(item_data)

                logger.info(f"Создано {len(schedule_items)} элементов для плана {plan_id}")
            else:
                logger.warning(f"Не удалось распарсить расписание для плана {plan_id}")

        except Exception as e:
            logger.error(f"Ошибка при генерации расписания для плана {plan_id}: {e}")

    def _parse_plan_schedule(self, generated_plan: str) -> List[Dict[str, Any]]:
        """
        Парсить сгенерированный план и извлечь элементы расписания
        """
        items = []

        try:
            # Ищем паттерны дат и тем в тексте
            # Примеры форматов:
            # "25.11 - Тема поста"
            # "26 ноября - Другая тема"
            # "27.11.2024 - Еще одна тема"

            date_patterns = [
                r'(\d{1,2}[./]\d{1,2}(?:[./]\d{4})?)\s*[-–—]\s*(.+)',
                r'(\d{1,2}\s+\w+\s+\d{4})\s*[-–—]\s*(.+)',
                r'(\d{1,2}\s+\w+)\s*[-–—]\s*(.+)',
            ]

            for pattern in date_patterns:
                matches = re.finditer(pattern, generated_plan, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    date_str = match.group(1).strip()
                    title = match.group(2).strip()

                    # Парсим дату
                    try:
                        pub_date = self._parse_date(date_str)
                        if pub_date and pub_date > datetime.now():
                            items.append({
                                "publication_date": pub_date,
                                "content_title": title[:255],  # Ограничение по длине
                                "content_text": f"Запланированная публикация: {title}",
                                "status": PublicationStatus.SCHEDULED,
                                "notification_sent": False
                            })
                    except Exception as e:
                        logger.warning(f"Не удалось распарсить дату '{date_str}': {e}")
                        continue

            # Если не нашли даты в тексте, создаем расписание автоматически
            if not items:
                items = self._generate_auto_schedule(generated_plan)

        except Exception as e:
            logger.error(f"Ошибка при парсинге расписания: {e}")
            # В случае ошибки создаем базовое расписание
            items = self._generate_auto_schedule(generated_plan)

        return items

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Парсить строку даты в объект datetime
        """
        try:
            # Убираем лишние символы
            date_str = date_str.strip()

            # Форматы для парсинга
            formats = [
                '%d.%m.%Y',
                '%d.%m',
                '%d/%m/%Y',
                '%d/%m',
                '%d %B %Y',
                '%d %b %Y',
                '%d %B',
                '%d %b'
            ]

            current_year = datetime.now().year

            for fmt in formats:
                try:
                    if 'Y' not in fmt:
                        # Если год не указан, используем текущий
                        date_str_with_year = f"{date_str}.{current_year}"
                        fmt_with_year = fmt + '.%Y'
                        return datetime.strptime(date_str_with_year, fmt_with_year)
                    else:
                        return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue

            return None

        except Exception as e:
            logger.warning(f"Не удалось распарсить дату '{date_str}': {e}")
            return None

    def _generate_auto_schedule(self, generated_plan: str) -> List[Dict[str, Any]]:
        """
        Генерировать автоматическое расписание, если не удалось распарсить даты
        """
        items = []

        try:
            # Извлекаем примерные темы из плана
            lines = generated_plan.split('\n')
            topics = []

            for line in lines:
                line = line.strip()
                # Ищем строки, которые могут быть темами постов
                if any(keyword in line.lower() for keyword in ['пост', 'статья', 'новост', 'истор', 'совет', 'событ']):
                    # Убираем номера и символы в начале
                    clean_line = re.sub(r'^[\d\.\-\*\•\s]+', '', line).strip()
                    if clean_line and len(clean_line) > 10:
                        topics.append(clean_line[:100])

            # Если тем не нашли, создаем общие
            if not topics:
                topics = [
                    "Обновление о деятельности фонда",
                    "История успеха",
                    "Полезные советы",
                    "Анонс мероприятия"
                ]

            # Генерируем расписание на ближайшие дни
            start_date = datetime.now().replace(hour=14, minute=0, second=0, microsecond=0)

            for i, topic in enumerate(topics[:5]):  # Максимум 5 постов
                pub_date = start_date + timedelta(days=i)
                items.append({
                    "publication_date": pub_date,
                    "content_title": topic,
                    "content_text": f"Запланированная публикация: {topic}",
                    "status": PublicationStatus.SCHEDULED,
                    "notification_sent": False
                })

        except Exception as e:
            logger.error(f"Ошибка при автогенерации расписания: {e}")

        return items


    async def save_content_plan(
            self,
            content_plan: ContentPlan,
    ) -> int:
        """
        Сохранить контент-план в базу данных
        
        Args:
            content_plan (ContentPlan): Контент-план
        
        Returns:
            ID созданного плана
        """
        try:
            plan_id = self.repository.create(content_plan)
            plan = self.repository.get_by_id(plan_id)

            # Генерируем расписание публикаций
            await self._generate_schedule(plan.id_, content_plan)

            logger.info(f"Контент-план {plan.id_} сохранен для пользователя {plan.user_id}")
            return plan.id_

        except Exception as e:
            logger.error(f"Ошибка при сохранении контент-плана: {e}")
            raise



    async def get_user_plans(self, user_id: int) -> tuple[ContentPlan, ...]:
        """
        Получить все планы пользователя
        """
        plans = self.repository.get_all_by_user_id(user_id)
        return plans

    async def delete_plan(self, plan_id: int, user_id: int) -> bool:
        """
        Удалить план (мягкое удаление)
        """
        try:
            success = self.repository.delete(plan_id, user_id)
            return success
        except Exception as e:
            logger.error(f"Ошибка при удалении плана {plan_id}: {e}")
            return False


    async def generate_content_plan(
            self,
            context: PlanPromptContext
    ) -> ContentPlan:

        logger.info(f"Генерация контент-плана.")

        prompt = self.prompt_builder.build_structured_content_plan_prompt(context)
        logger.info(f"Сформирован промпт длиной {len(prompt)} символов")

        raw_response = await self.gpt_client.generate(prompt, self.SYSTEM_PROMPT)
        generated_text = self.response_processor.process_response(raw_response)

        try:
            items_data = self.response_processor.parse_json_list(generated_text)
        except Exception as e:
            logger.error(f"Ошибка парсинга ответа модели: {e}")
            raise ValueError("Модель вернула некорректный формат данных. Попробуйте еще раз.")

        # Преобразование данных в объекты ContentPlanItem
        plan_items = []
        for item in items_data:
            try:
                # Парсинг даты из ISO формата (YYYY-MM-DDTHH:MM:SS)
                pub_date = datetime.fromisoformat(item.get("publication_date"))

                content_item = ContentPlanItem(
                    id_=None,  # Еще не сохранено в БД
                    content_plan_id=0,  # Будет присвоено после сохранения плана
                    publication_date=pub_date,
                    content_title=item["content_title"],
                    content_text=item["content_text"],
                    status=PublicationStatus.SCHEDULED,
                    notification_sent=False,
                    notification_sent_at=None
                )
                plan_items.append(content_item)
            except Exception as e:
                logger.warning(f"Пропуск некорректного элемента плана: {item}. Ошибка: {e}")
                continue

        if not plan_items:
            raise ValueError("Не удалось сформировать ни одного пункта плана из ответа модели.")

        # Сборка итогового объекта ContentPlan
        # Используем данные из context для заполнения мета-информации

        content_plan = ContentPlan(
            id_=None,
            user_id=context.user_id,
            plan_name=f"Контент-план: {context.themes}"[:100],  # Ограничение длины на всякий случай
            period=context.period,
            frequency=context.frequency,
            topics=context.themes,
            details=f"Сгенерировано для: {context.themes}",
            plan_data={"raw_items_count": len(items_data)},  # Можно сохранить метаданные
            items=tuple(plan_items)
        )

        logger.info(f"Успешно сгенерирован структурированный план на {len(plan_items)} постов")
        return content_plan

    async def get_plan_by_id(self, plan_id: int) -> Optional[ContentPlan]:
        """
        Получить контент-план по ID.
        """
        try:
            plan = self.repository.get_by_id(plan_id)
            return plan
        except Exception as e:
            logger.error(f"Ошибка при получении плана {plan_id}: {e}")
            return None

    async def get_plan_item_by_id(self, item_id: int) -> Optional[ContentPlanItem]:
        """
        Получить конкретный элемент (пост) контент-плана по ID.
        """
        try:
            return self.repository.get_content_plan_item_by_id(item_id)
        except Exception as e:
            logger.error(f"Ошибка при получении элемента плана {item_id}: {e}")
            return None
