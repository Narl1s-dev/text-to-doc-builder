# План проекта: Text To Doc Builder

## 1. Идея продукта

Проект принимает API-запрос в свободной, разговорной форме и сразу создает документ. Прототип сфокусирован на `.docx`, но архитектура должна быть готова к будущему расширению на другие форматы: `.pptx`, `.xlsx`, `.pdf` и другие.

Базовый сценарий:

1. Внешний клиент отправляет `POST /documents` с текстом запроса.
2. Backend валидирует запрос.
3. Backend сохраняет исходные данные и метаданные.
4. Backend отправляет пользовательский запрос в LLM через OpenRouter.
5. LLM разбирает свободный текст, извлекает ограничения и дополняет недостающие параметры стандартными значениями.
6. Backend получает структурированный план генерации.
7. Backend выбирает генератор под нужный формат.
8. Для прототипа backend создает `.docx`.
9. Backend сохраняет файл и возвращает ссылку на скачивание.

Главный принцип: пользователь может писать естественным языком, а сервис сам переводит запрос в структурированную спецификацию документа.

## 2. Целевой результат

В итоге мы хотим получить backend-сервис, который умеет:

- принимать REST API-запросы на создание документов;
- на первом этапе создавать `.docx`;
- не быть архитектурно привязанным только к `.docx`;
- разбирать свободный пользовательский запрос через LLM;
- использовать базовые значения, если пользователь не указал стиль, язык, структуру, объем или форматирование;
- обращаться к OpenRouter для генерации, структурирования или улучшения содержимого;
- хранить исходный запрос, структурированную спецификацию, ответ LLM и готовый файл;
- возвращать клиенту результат: статус, имя файла и ссылку на скачивание;
- позже подключать генераторы `.pptx`, `.xlsx`, `.pdf` и других форматов без переписывания API.

## 3. Подход к форматам

Прототип делает только `.docx`, но ядро проекта должно работать не с конкретным Word-файлом, а с абстрактной спецификацией результата.

Для этого вводим два уровня:

1. `GenerationSpec` - что хочет пользователь и какие ограничения нужно применить.
2. `ArtifactPlan` - структурированный план конкретного артефакта, который можно отдать генератору.

Для `.docx` `ArtifactPlan` будет похож на план документа. Для `.pptx` это будет план презентации со слайдами. Для `.xlsx` - план книги с листами, таблицами и формулами. Для `.pdf` возможны два пути: прямой PDF-генератор или промежуточный HTML/CSS с последующей конвертацией.

## 4. Предлагаемый стек

Стартовый стек:

- Язык: Python.
- API: FastAPI.
- Валидация данных: Pydantic.
- База данных: SQLite для прототипа, PostgreSQL для production.
- ORM/миграции: SQLAlchemy + Alembic.
- HTTP-клиент для OpenRouter: httpx.
- Генерация `.docx`: python-docx.
- Хранилище файлов: локальная папка `storage/artifacts` для прототипа.
- Тесты: pytest.

Кандидаты для будущих форматов:

- `.pptx`: python-pptx.
- `.xlsx`: openpyxl или XlsxWriter.
- `.pdf`: HTML/CSS -> PDF через WeasyPrint или другой HTML-to-PDF renderer.
- `.html`: Jinja2-шаблоны + HTML sanitizer, если понадобится отдавать HTML как самостоятельный формат.

Важно: LLM может помогать создавать структуру, текст, таблицы, HTML или JSON-план, но финальную сборку файла должен выполнять backend. Так результат будет валидируемым, повторяемым и контролируемым.

## 5. Архитектура

```text
External Client
      |
      v
Backend API
      |
      v
Generation Pipeline
      |
      +--> Request Persistence
      +--> LLM Request Parser
      +--> Defaults Resolver
      +--> OpenRouter Client
      +--> Artifact Planning
      +--> Format Renderer Registry
      |       |
      |       +--> DOCX Renderer
      |       +--> Future PPTX Renderer
      |       +--> Future XLSX Renderer
      |       +--> Future PDF Renderer
      |
      +--> File Storage
      |
      v
Artifact Result
```

## 6. Основной pipeline генерации

### 6.1 Прием запроса

Backend получает от клиента:

- свободный текст запроса;
- желаемый формат, если клиент указал его явно;
- дополнительные структурированные параметры, если они есть;
- технические метаданные клиента.

Минимальный запрос может состоять только из поля `prompt`.

### 6.2 LLM-разбор ограничений

Разбор ограничений сразу делаем через LLM. Пользователь будет писать в разговорной форме, поэтому простые правила подходят только как вспомогательная валидация, а не как основной механизм.

Задача `LLMRequestParser`:

- понять, какой тип документа нужен;
- определить формат результата;
- извлечь тему, цель, аудиторию, стиль, язык, объем и структуру;
- выделить исходные факты, которые нельзя искажать;
- определить, нужно ли дописать текст, переформулировать его или только оформить;
- вернуть структурированный JSON;
- заполнить недостающие поля стандартными значениями.

Примеры пользовательских запросов:

```text
Сделай служебную записку на 1 страницу по этому тексту, официальным стилем.
```

```text
Подготовь документ с планом урока. Нужны цель, материалы, ход занятия и домашнее задание.
```

```text
Собери краткий договор в деловом стиле, без сложных юридических формулировок.
```

### 6.3 Базовые значения и плейсхолдеры

Если пользователь не указал часть параметров, сервис должен подставить стандартные значения. Это должно происходить явно и сохраняться в `GenerationSpec`.

Базовые значения для прототипа:

```json
{
  "output_format": "docx",
  "language": "ru",
  "document_type": "general_document",
  "title": "Документ",
  "audience": "general",
  "tone": "neutral",
  "style": "business",
  "length": {
    "mode": "medium",
    "max_pages": null
  },
  "formatting": {
    "page_size": "A4",
    "orientation": "portrait",
    "font_family": "Times New Roman",
    "font_size": 12,
    "line_spacing": 1.15,
    "paragraph_spacing_after": 6,
    "margins": {
      "top_cm": 2,
      "right_cm": 1.5,
      "bottom_cm": 2,
      "left_cm": 3
    }
  },
  "structure": {
    "include_title": true,
    "include_summary": false,
    "sections": []
  }
}
```

Плейсхолдеры нужны не только как значения по умолчанию, но и как защита от неполных запросов. Например, если пользователь не указал название, LLM может сгенерировать его из темы. Если тема тоже неясна, используется `"Документ"` и сохраняется предупреждение в метаданных.

### 6.4 GenerationSpec

`GenerationSpec` - нормализованное описание того, что нужно создать.

Пример:

```json
{
  "output_format": "docx",
  "document_type": "memo",
  "title": "Служебная записка",
  "language": "ru",
  "audience": "руководитель проекта",
  "tone": "formal",
  "style": "official",
  "source_facts": [
    "Срок проекта нужно перенести на две недели",
    "Причина: задержка поставки материалов"
  ],
  "constraints": {
    "max_pages": 1,
    "must_include": ["причина", "предложение", "ожидаемый результат"],
    "must_not_include": []
  },
  "formatting": {
    "page_size": "A4",
    "font_family": "Times New Roman",
    "font_size": 12
  }
}
```

### 6.5 ArtifactPlan

`ArtifactPlan` - план конкретного файла, который получает renderer.

Для `.docx`:

```json
{
  "artifact_type": "document",
  "output_format": "docx",
  "title": "Служебная записка",
  "blocks": [
    { "type": "heading", "level": 1, "text": "Служебная записка" },
    { "type": "paragraph", "text": "Прошу перенести срок..." },
    {
      "type": "bullet_list",
      "items": ["Причина переноса", "Предлагаемый срок", "Ожидаемый результат"]
    }
  ],
  "formatting": {
    "page_size": "A4",
    "font_family": "Times New Roman",
    "font_size": 12
  }
}
```

В будущем для `.pptx` и `.xlsx` будут отдельные варианты `ArtifactPlan`, но общий pipeline останется тем же.

### 6.6 Обращение к OpenRouter

OpenRouter используется в двух логических шагах:

1. `LLMRequestParser` - превращает свободный пользовательский запрос в `GenerationSpec`.
2. `LLMArtifactPlanner` - превращает `GenerationSpec` в `ArtifactPlan`.

На первом этапе эти два шага можно объединить в один вызов OpenRouter, чтобы быстрее собрать прототип. Но интерфейсы лучше сразу разделить, чтобы позже можно было независимо менять парсинг запроса и построение документа.

Компоненты:

- `OpenRouterClient` - низкоуровневый HTTP-клиент.
- `PromptBuilder` - сборка промптов.
- `LLMRequestParser` - парсинг пользовательского запроса.
- `DefaultsResolver` - применение стандартных значений.
- `LLMArtifactPlanner` - построение плана артефакта.
- `LLMResponseValidator` - проверка JSON и схемы.

### 6.7 Генерация файла

Финальную генерацию выполняет renderer, выбранный по `output_format`.

Для прототипа:

- `DocxRenderer` получает `ArtifactPlan`;
- создает `.docx` через python-docx;
- сохраняет файл в `storage/artifacts`;
- возвращает путь, имя файла и размер.

Будущие renderer-ы:

- `PptxRenderer`;
- `XlsxRenderer`;
- `PdfRenderer`;
- `HtmlRenderer`.

## 7. API первого прототипа

### Создать документ

`POST /documents`

Request:

```json
{
  "prompt": "Сделай служебную записку на 1 страницу официальным стилем. Тема: перенос сроков проекта из-за задержки поставки материалов.",
  "output_format": "docx",
  "overrides": {
    "language": "ru",
    "title": "Служебная записка"
  },
  "metadata": {
    "client": "prototype",
    "external_user_id": "123456"
  }
}
```

Минимальный request:

```json
{
  "prompt": "Сделай краткий документ по итогам встречи"
}
```

Response при успешной генерации:

```json
{
  "document_id": "doc_123",
  "status": "ready",
  "output_format": "docx",
  "file_name": "document_doc_123.docx",
  "download_url": "/documents/doc_123/download",
  "warnings": []
}
```

Response при ошибке:

```json
{
  "document_id": "doc_123",
  "status": "failed",
  "error_message": "Не удалось создать документ"
}
```

### Скачать документ

`GET /documents/{document_id}/download`

Возвращает готовый файл.

### Получить информацию о документе

`GET /documents/{document_id}`

Response:

```json
{
  "document_id": "doc_123",
  "status": "ready",
  "output_format": "docx",
  "file_name": "document_doc_123.docx",
  "download_url": "/documents/doc_123/download",
  "created_at": "2026-05-25T19:00:00Z"
}
```

### Проверка состояния сервиса

`GET /health`

Response:

```json
{
  "status": "ok"
}
```

## 8. Основные сущности

### GenerationRequest

Хранит входной API-запрос.

Поля:

- `id`;
- `prompt`;
- `requested_output_format`;
- `overrides`;
- `metadata`;
- `created_at`.

### Artifact

Хранит результат генерации.

Поля:

- `id`;
- `request_id`;
- `output_format`;
- `status`;
- `title`;
- `file_name`;
- `file_path`;
- `file_size`;
- `error_message`;
- `warnings`;
- `created_at`;
- `updated_at`.

### LLMGeneration

Хранит сведения об обращении к OpenRouter.

Поля:

- `id`;
- `request_id`;
- `stage`;
- `provider`;
- `model`;
- `prompt_version`;
- `input_payload`;
- `raw_output`;
- `parsed_output`;
- `error_message`;
- `created_at`.

### Template

Описывает шаблон оформления.

Поля:

- `id`;
- `name`;
- `artifact_type`;
- `output_format`;
- `description`;
- `settings`;
- `created_at`;
- `updated_at`.

## 9. Статусы

В прототипе генерация запускается сразу, поэтому основные статусы такие:

- `processing` - файл создается;
- `ready` - файл готов;
- `failed` - генерация завершилась ошибкой.

Статус `pending` понадобится позже, если появится очередь задач.

## 10. Предварительная структура проекта

```text
text-to-doc-builder/
  app/
    main.py
    api/
      routes/
        health.py
        documents.py
    core/
      config.py
      logging.py
      errors.py
    db/
      session.py
      models.py
      migrations/
    schemas/
      generation_request.py
      generation_spec.py
      artifact.py
      artifact_plan.py
    services/
      generation_service.py
      generation_pipeline.py
      defaults_resolver.py
      prompt_builder.py
      storage_service.py
    llm/
      openrouter_client.py
      request_parser.py
      artifact_planner.py
      response_validator.py
      schemas.py
    renderers/
      base.py
      registry.py
      docx_renderer.py
      future_pptx_renderer.py
      future_xlsx_renderer.py
      future_pdf_renderer.py
    repositories/
      generation_request_repository.py
      artifact_repository.py
      llm_generation_repository.py
      template_repository.py
  storage/
    artifacts/
  tests/
    unit/
    integration/
  alembic/
  .env.example
  pyproject.toml
  README.md
  plan.md
```

В прототипе реализуем только `docx_renderer.py`. Файлы `future_*` в структуре показывают направление развития, но создавать пустые модули без пользы не обязательно.

## 11. Конфигурация окружения

Минимальный `.env.example`:

```text
APP_ENV=local
APP_HOST=0.0.0.0
APP_PORT=8000

DATABASE_URL=sqlite:///./storage/app.db
ARTIFACT_STORAGE_PATH=./storage/artifacts

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=
OPENROUTER_TIMEOUT_SECONDS=60

DEFAULT_OUTPUT_FORMAT=docx
DEFAULT_LANGUAGE=ru
DEFAULT_STYLE=business
DEFAULT_TONE=neutral
DEFAULT_FONT_FAMILY=Times New Roman
DEFAULT_FONT_SIZE=12

PUBLIC_BASE_URL=http://localhost:8000
API_INTERNAL_TOKEN=
```

`API_INTERNAL_TOKEN` нужен для защиты API от случайных или чужих вызовов. На этапе локального прототипа его можно сделать опциональным, но лучше сразу заложить поддержку.

## 12. Работа с OpenRouter

Для прототипа OpenRouter можно вызвать один раз и попросить модель вернуть сразу `GenerationSpec` и `ArtifactPlan`.

Требования к ответу LLM:

- строго валидный JSON;
- никаких markdown-блоков вокруг JSON;
- заполненные значения по умолчанию;
- явное поле `warnings`, если часть данных пришлось предположить;
- сохранение фактов пользователя без искажений;
- структура, пригодная для renderer-а.

Пример верхнего уровня ответа:

```json
{
  "generation_spec": {
    "output_format": "docx",
    "document_type": "memo",
    "title": "Служебная записка"
  },
  "artifact_plan": {
    "artifact_type": "document",
    "output_format": "docx",
    "title": "Служебная записка",
    "blocks": []
  },
  "warnings": []
}
```

После получения ответа backend обязательно валидирует JSON через Pydantic. Если JSON невалидный, допускается одна LLM-попытка исправления.

## 13. Этапы разработки

### Этап 1. Каркас backend

- Создать FastAPI-приложение.
- Добавить `GET /health`.
- Добавить конфигурацию через `.env`.
- Подготовить структуру папок.
- Добавить базовое логирование.

### Этап 2. Endpoint создания документа

- Добавить `POST /documents`.
- Добавить Pydantic-схемы запроса и ответа.
- Добавить авторизацию через внутренний токен.
- Сохранять входной запрос в SQLite.
- Создавать запись artifact со статусом `processing`.

### Этап 3. LLM-парсинг и дефолты

- Добавить схемы `GenerationSpec` и `ArtifactPlan`.
- Реализовать `DefaultsResolver`.
- Реализовать `PromptBuilder`.
- Реализовать `OpenRouterClient`.
- Реализовать `LLMRequestParser` и `LLMArtifactPlanner`.
- Добавить валидацию ответа LLM.

### Этап 4. Генерация `.docx`

- Реализовать `RendererRegistry`.
- Реализовать `DocxRenderer`.
- Сохранять документы в `storage/artifacts`.
- Добавить `GET /documents/{document_id}/download`.
- Обновлять статус artifact на `ready` или `failed`.

### Этап 5. Сквозной прототип

- Один запрос `POST /documents` должен создавать готовый `.docx`.
- Проверить минимальный запрос только с `prompt`.
- Проверить запрос с `overrides`.
- Проверить ошибки OpenRouter.
- Проверить ошибки генерации файла.
- Добавить тесты на pipeline.

### Этап 6. Подготовка к новым форматам

- Зафиксировать интерфейс `BaseRenderer`.
- Добавить форматный enum.
- Добавить валидацию поддерживаемых форматов.
- Подготовить тесты, которые проверяют выбор renderer-а.
- Описать будущие `PptxRenderer`, `XlsxRenderer`, `PdfRenderer`.

### Этап 7. Production-подготовка

- Перейти на PostgreSQL.
- Добавить миграции Alembic.
- Добавить Dockerfile и docker-compose.
- Добавить внешнее файловое хранилище при необходимости.
- Добавить структурированное логирование.
- Добавить мониторинг ошибок.
- Добавить очередь задач, если синхронная генерация станет слишком долгой.

## 14. Риски и решения

### Долгая генерация

Риск: обращение к OpenRouter и создание файла могут занимать слишком долго для синхронного API.

Решение для прототипа:

- ставить разумный timeout;
- возвращать понятную ошибку;
- логировать длительность этапов.

Решение позже:

- очередь задач;
- статус `pending`;
- polling через `GET /documents/{document_id}`;
- webhook/callback для клиента.

### Нестабильный JSON от LLM

Риск: модель может вернуть текст вместо JSON или нарушить схему.

Решение:

- строгий промпт;
- Pydantic-валидация;
- одна автоматическая попытка исправления JSON;
- сохранение сырого ответа модели для диагностики.

### Ошибки OpenRouter

Риск: внешний провайдер может быть недоступен, вернуть ошибку лимита или таймаут.

Решение:

- отдельный `OpenRouterClient`;
- timeout;
- обработка HTTP-ошибок;
- сохранение ошибки в `LLMGeneration`;
- понятный ответ клиенту.

### Расширение форматов

Риск: если `.docx`-логика попадет в общий pipeline, будущие `.pptx`, `.xlsx` и `.pdf` будет сложно добавить.

Решение:

- общий `GenerationSpec`;
- форматные варианты `ArtifactPlan`;
- общий интерфейс `BaseRenderer`;
- registry renderer-ов;
- изоляция форматных библиотек внутри конкретных renderer-ов.

### Безопасность API

Риск: endpoint генерации может быть вызван кем угодно.

Решение:

- внутренний API-токен;
- лимиты размера входного текста;
- rate limiting позже;
- не отдавать локальные пути файлов наружу.

## 15. Принципы проекта

- Backend является самостоятельным API-сервисом.
- Прототип создает `.docx`, но ядро проектируется под разные форматы.
- Пользовательский запрос разбирается через LLM, потому что вход будет свободным и разговорным.
- Все недостающие параметры заполняются стандартными значениями.
- OpenRouter используется только через отдельный слой клиента и LLM-сервисов.
- Renderer не должен знать, какая LLM использовалась.
- LLM должна возвращать структурированный план, а не готовый файл.
- Исходный запрос, ответ LLM, нормализованная спецификация и созданный файл хранятся отдельно.
- Ошибки должны быть видны через API и сохранены для диагностики.
- Локальная разработка должна запускаться одной командой.

## 16. Что делаем следующим шагом

Следующий практический шаг - создать каркас FastAPI-проекта:

1. `pyproject.toml`;
2. пакет `app`;
3. endpoint `GET /health`;
4. конфигурацию `.env`;
5. endpoint `POST /documents`;
6. схемы `GenerationSpec` и `ArtifactPlan`;
7. `OpenRouterClient`;
8. `DefaultsResolver`;
9. `RendererRegistry`;
10. простой `DocxRenderer`;
11. локальное сохранение файлов в `storage/artifacts`.

После этого можно будет собрать первый рабочий сквозной прототип: клиент отправляет свободный запрос в `POST /documents`, backend через OpenRouter получает план, генерирует `.docx` и возвращает ссылку на скачивание.
