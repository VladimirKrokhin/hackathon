# Архитектура проекта ContentHelper

Документ описывает основные сущности и компоненты проекта для команды разработчиков.

## Структура проекта

Проект организован по принципу слоистой архитектуры:

```
src/
├── infrastructure/     # Инфраструктурный слой (внешние зависимости)
│   ├── gpt.py         # Абстракции для работы с GPT-моделями
│   ├── prompt_builder.py  # Построение промптов для LLM
│   ├── response_processor.py  # Обработка ответов от LLM
│   └── card_generation.py     # Генерация визуальных карточек
├── services/          # Бизнес-логика
│   └── content_generation.py  # Сервис генерации контента
├── bot/               # Telegram-бот слой
│   ├── handlers/      # Обработчики сообщений
│   ├── keyboards/     # Клавиатуры бота
│   ├── states.py      # FSM состояния
│   └── utils.py       # Вспомогательные функции
├── config.py          # Конфигурация приложения
├── bootstrap.py       # Dependency Injection
└── main.py            # Точка входа
```

---

## Основные сущности

### 1. Инфраструктурный слой (`infrastructure/`)

#### 1.1. GPT клиенты (`infrastructure/gpt.py`)

**Иерархия классов:**
```
AbstractGPT (ABC)
    └── ApiGPT (ABC)
        └── YandexGPT
```

**`AbstractGPT`** — базовый интерфейс для всех GPT-моделей:
- `model_name: str` — имя модели для логирования
- `generate(prompt: str) -> Dict` — генерация ответа по промпту

**`ApiGPT`** — абстрактный класс для GPT, работающих через HTTP API:
- Управляет HTTP-запросами (`_make_request`)
- Требует реализации `build_payload(prompt: str) -> Dict`
- Обрабатывает ошибки сети, таймауты, парсинг JSON

**`YandexGPT`** — конкретная реализация для YandexGPT API:
- Использует конфигурацию из `config.py`
- Формирует payload в формате YandexGPT API
- Настраивается через `YANDEXGPT_*` параметры в конфиге

**Пример использования:**
```python
gpt = YandexGPT()
response = await gpt.generate("Ваш промпт здесь")
```

---

#### 1.2. Построение промптов (`infrastructure/prompt_builder.py`)

**`PromptContext`** — dataclass для структурированных данных пользователя:
```python
@dataclass
class PromptContext:
    goal: str                    # Цель поста (например, "Привлечь волонтеров")
    audience: list[str]          # Целевая аудитория
    platform: str                # Платформа (ВК, Telegram, сайт)
    content_format: list[str]    # Формат контента
    volume: str                  # Объем текста
    event_details: dict[str, str] # Детали мероприятия (если есть)
    has_event: bool              # Есть ли мероприятие
    
    @classmethod
    def from_dict(cls, data: Mapping) -> "PromptContext":
        # Конвертация из словаря (для совместимости)
```

**`AbstractPromptBuilder`** — интерфейс для построителей промптов:
- `build_prompt(user_data: PromptContext, user_text: str) -> str`

**`YandexGPTPromptBuilder`** — реализация для YandexGPT:
- Формирует структурированный промпт на основе контекста
- Адаптирует стиль под аудиторию (`_get_audience_style`)
- Добавляет требования платформы (`_get_platform_requirements`)
- Обрабатывает информацию о мероприятиях

**Особенности:**
- Автоматически определяет стиль текста на основе аудитории
- Добавляет примеры удачных постов для вдохновения
- Нормализует списки (строки → списки строк)

---

#### 1.3. Обработка ответов (`infrastructure/response_processor.py`)

**`AbstractResponseProcessor`** — интерфейс:
- `process_response(response: Dict) -> str` — извлекает текст из ответа API

**`YandexGPTResponseProcessor`** — реализация для YandexGPT:
- Извлекает текст из структуры ответа YandexGPT API
- Выполняет постобработку:
  - Удаляет служебные инструкции
  - Исправляет форматирование
  - Убирает лишние пробелы

**Структура ответа YandexGPT:**
```json
{
  "result": {
    "alternatives": [{
      "message": {
        "text": "Сгенерированный текст..."
      }
    }]
  }
}
```

---

#### 1.4. Генерация карточек (`infrastructure/card_generation.py`)

**`BaseCardGenerator`** — абстрактный класс:
- `render_card(template_name, data, size) -> bytes` — генерация карточки
- `load_template(template_name) -> str` — загрузка шаблона

**`PlaywrightCardGenerator`** — реализация через Playwright:
- Принимает `Browser` в конструкторе (DI)
- Рендерит HTML-шаблоны в PNG изображения
- Использует Playwright для скриншотов

**Процесс генерации:**
1. Загрузка HTML-шаблона
2. Подстановка данных (`template.format(...)`)
3. Рендеринг через Playwright
4. Скриншот страницы
5. Возврат PNG в виде bytes

**Шаблоны:**
- Хранятся в `templates/*.html`
- Используют Python `.format()` для подстановки данных
- Поддерживают параметры: `title`, `content`, `primary_color`, `org_name`, и т.д.

---

### 2. Сервисный слой (`services/`)

#### 2.1. ContentGenerationService (`services/content_generation.py`)

**Назначение:** Управление процессом генерации контента.

**Зависимости (через DI):**
- `prompt_builder: AbstractPromptBuilder`
- `gpt_client: AbstractGPT`
- `response_processor: AbstractResponseProcessor`

**Метод:**
```python
async def generate_content(
    user_data: Union[Dict, PromptContext], 
    user_text: str
) -> str
```

**Процесс:**
1. Конвертирует `user_data` в `PromptContext` (если нужно)
2. Строит промпт через `prompt_builder`
3. Отправляет запрос к GPT через `gpt_client`
4. Обрабатывает ответ через `response_processor`
5. Возвращает готовый текст

**Особенности:**
- Принимает как словарь, так и `PromptContext` (обратная совместимость)
- Инкапсулирует всю логику генерации в одном месте

---

### 3. Слой бота (`bot/`)

#### 3.1. Состояния (`bot/states.py`)

**`ContentGeneration`** — FSM группа состояний:
```python
class ContentGeneration(StatesGroup):
    waiting_for_goal           # Ожидание выбора цели
    waiting_for_audience      # Ожидание выбора аудитории
    waiting_for_platform       # Ожидание выбора платформы
    waiting_for_format         # Ожидание выбора формата
    waiting_for_has_event      # Есть ли мероприятие?
    waiting_for_event_details  # Детали мероприятия
    waiting_for_volume         # Объем контента
    waiting_for_user_text      # Дополнительная информация от пользователя
    waiting_for_confirmation   # Подтверждение результата
```

**Использование:** Управляет диалогом с пользователем через FSM (Finite State Machine).

---

#### 3.2. Обработчики (`bot/handlers/`)

**`questionnaire.py`** — сбор данных от пользователя:
- Обрабатывает ответы на вопросы анкеты
- Переводит пользователя между состояниями
- Валидирует ввод через клавиатуры

**`generation.py`** — генерация контента:
- Получает финальный текст от пользователя
- Вызывает `ContentGenerationService`
- Генерирует визуальные карточки
- Отправляет результат пользователю

**`start.py`** — команда `/start`

**`callbacks.py`** — обработка inline-кнопок

**`fallback.py`** — обработка неизвестных команд

---

#### 3.3. Утилиты (`bot/utils.py`)

Вспомогательные функции для работы с данными:
- `get_color_by_goal(goal) -> str` — цвет по цели
- `get_title_by_goal(goal) -> str` — заголовок по цели
- `get_template_by_platform(platform) -> str` — шаблон по платформе
- `get_caption_for_card_type(card_type, platform) -> str` — подпись для карточки

**Константы:**
- `GOAL_PRIMARY_COLORS` — цвета для разных целей
- `PLATFORM_TEMPLATES` — маппинг платформ на шаблоны
- `DEMO_CONTENT_BY_GOAL` — демо-контент для fallback

---

### 4. Конфигурация (`config.py`)

**`Config`** — класс настроек (Pydantic BaseSettings):
- Загружает переменные из `.env`
- Валидирует обязательные параметры
- Содержит настройки для:
  - Telegram Bot Token
  - YandexGPT API (ключ, каталог, модель, температура, токены)
  - Размеры карточек для разных платформ
  - Таймауты

**Доступ:** Глобальный экземпляр `config = Config()`

---

### 5. Dependency Injection (`bootstrap.py`)

**Назначение:** Инициализация и связывание зависимостей.

**Функции:**
- `init_browser() -> tuple[Browser, Any]` — инициализация Playwright
- `close_browser(browser, playwright)` — закрытие браузера
- `build_yandexgpt_content_generation_service() -> ContentGenerationService` — создание сервиса

**Экспорт:**
- `get_content_generation_service` — готовая функция для получения сервиса

**Принцип:** Все зависимости создаются в одном месте, что упрощает тестирование и замену компонентов.

---

## Поток данных

### Генерация контента:

```
Пользователь → Bot Handler (questionnaire.py)
    ↓
FSM State (waiting_for_user_text)
    ↓
Bot Handler (generation.py)
    ↓
ContentGenerationService.generate_content()
    ↓
    ├─→ PromptBuilder.build_prompt() → prompt: str
    ├─→ GPT.generate(prompt) → raw_response: Dict
    └─→ ResponseProcessor.process_response() → text: str
    ↓
Готовый текст поста
    ↓
CardGenerator.render_card() → image: bytes
    ↓
Пользователь получает текст + картинки
```

---

## Принципы проектирования

1. **Разделение ответственности:**
   - `infrastructure/` — работа с внешними API и инструментами
   - `services/` — бизнес-логика
   - `bot/` — интерфейс пользователя

2. **Абстракции:**
   - Все ключевые компоненты имеют абстрактные интерфейсы
   - Легко заменить реализацию (например, другой GPT-провайдер)

3. **Dependency Injection:**
   - Зависимости передаются через конструкторы
   - Централизованная инициализация в `bootstrap.py`

4. **Типизация:**
   - Использование dataclass для структурированных данных (`PromptContext`)
   - Type hints для всех публичных методов

---

## Расширение проекта

### Добавление нового GPT-провайдера:

1. Создать класс, наследующий `ApiGPT` или `AbstractGPT`
2. Реализовать `build_payload()` и `model_name`
3. Создать соответствующий `ResponseProcessor`
4. Обновить `bootstrap.py` для создания нового сервиса

### Добавление нового шаблона карточки:

1. Создать HTML-файл в `templates/`
2. Использовать параметры: `{title}`, `{content}`, `{primary_color}`, и т.д.
3. Добавить маппинг в `bot/utils.py` → `PLATFORM_TEMPLATES`

### Изменение анкеты:

1. Добавить новое состояние в `bot/states.py`
2. Добавить обработчик в `bot/handlers/questionnaire.py`
3. Обновить `PromptContext` (если нужны новые поля)

---

## Ключевые файлы для изучения

**Для понимания архитектуры:**
- `src/infrastructure/gpt.py` — иерархия GPT-классов
- `src/services/content_generation.py` — оркестрация генерации
- `src/bootstrap.py` — DI контейнер

**Для работы с ботом:**
- `src/bot/handlers/questionnaire.py` — сбор данных
- `src/bot/handlers/generation.py` — генерация контента
- `src/bot/states.py` — состояния диалога

**Для настройки:**
- `src/config.py` — все настройки проекта
- `.env` — переменные окружения

---

## Важные замечания

1. **Браузер Playwright:** Должен быть инициализирован до использования `CardGenerator`
2. **Конфигурация:** Все настройки GPT настраиваются через `config.py`, не хардкодятся
3. **Обработка ошибок:** Все компоненты логируют ошибки, но не все их обрабатывают (часть пробрасывается выше)
4. **Типизация:** `PromptContext` — предпочтительный способ передачи данных, но поддерживается и `Dict` для совместимости


