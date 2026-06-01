# План проекта: Text To Doc Builder

## 1. Идея продукта

Text To Doc Builder - backend-сервис, который принимает API-запрос в свободной разговорной форме, понимает требования пользователя и создает файл документа.

Прототип сфокусирован на `.docx`, но архитектура должна быть готова к будущим форматам: `.pptx`, `.xlsx`, `.pdf`, `.html` и другим.

Главная рекомендация по целевой архитектуре: не делать просто долгий async endpoint. Сервис должен быть job-based:

1. Клиент отправляет `POST /documents`.
2. Backend быстро валидирует запрос, создает job и возвращает `202 Accepted` с `document_id`.
3. Генерация идет в фоне через worker.
4. Клиент проверяет статус через `GET /documents/{document_id}`.
5. Когда файл готов, клиент скачивает его через `GET /documents/{document_id}/download`.

Так API остается быстрым, долгие LLM-вызовы и генерация файлов не блокируют HTTP-запрос, а ошибки можно надежно сохранять и диагностировать.

## 2. Целевой результат

В итоге нужен backend-сервис, который умеет:

- принимать REST API-запросы на создание документов;
- возвращать `202 Accepted` сразу после создания job;
- хранить статус генерации в базе данных;
- выполнять генерацию в фоне через worker-пул;
- ограничивать параллельность генерации, например 2-4 одновременные задачи;
- разбирать свободный пользовательский запрос через LLM;
- применять стандартные значения, если пользователь не указал стиль, язык, структуру, объем или форматирование;
- создавать для `.docx` структурированный `document_spec.json`;
- хранить внутри спецификации `content_markdown`, если текст удобнее вести в Markdown;
- генерировать Python-код для создания `.docx` через отдельный codegen LLM-шаг;
- запускать LLM-generated code только в Docker sandbox;
- валидировать готовый `.docx`;
- делать 1-2 repair retry при ошибке кода или валидации;
- сохранять исходный запрос, спецификацию, LLM-ответы, sandbox-логи и готовый файл;
- отдавать клиенту статус, ошибку или ссылку на скачивание;
- иметь минимальный web UI для быстрого ручного тестирования сервиса;
- разворачиваться на своем сервере в тестовом окружении;
- позже подключать `.pptx`, `.xlsx`, `.pdf` и другие форматы без переписывания API.

## 3. API-модель

### Создать задачу генерации

`POST /documents`

Запрос:

```json
{
  "prompt": "Сделай коммерческое предложение для клиента. Деловой стиль, 2 страницы, добавь таблицу цен.",
  "overrides": {
    "language": "ru"
  },
  "metadata": {
    "client": "prototype",
    "external_user_id": "123456"
  }
}
```

Минимальный запрос:

```json
{
  "prompt": "Сделай краткий документ по итогам встречи"
}
```

Ответ должен быть быстрым. `POST /documents` не ждет генерацию файла.

```json
{
  "document_id": "doc_123",
  "request_id": "req_123",
  "status": "queued",
  "output_format": "docx",
  "status_url": "/documents/doc_123",
  "download_url": null
}
```

HTTP-статус: `202 Accepted`.

### Получить статус

`GET /documents/{document_id}`

Пока задача в очереди:

```json
{
  "document_id": "doc_123",
  "status": "queued",
  "output_format": "docx",
  "file_name": null,
  "download_url": null,
  "error_message": null,
  "warnings": []
}
```

Пока задача выполняется:

```json
{
  "document_id": "doc_123",
  "status": "processing",
  "output_format": "docx",
  "current_stage": "codegen",
  "file_name": null,
  "download_url": null,
  "error_message": null,
  "warnings": []
}
```

Когда файл готов:

```json
{
  "document_id": "doc_123",
  "status": "ready",
  "output_format": "docx",
  "file_name": "doc_123.docx",
  "download_url": "/documents/doc_123/download",
  "error_message": null,
  "warnings": []
}
```

При ошибке:

```json
{
  "document_id": "doc_123",
  "status": "failed",
  "output_format": "docx",
  "file_name": null,
  "download_url": null,
  "error_message": "Не удалось создать документ",
  "warnings": ["Sandbox execution failed after 2 repair attempts."]
}
```

### Скачать готовый файл

`GET /documents/{document_id}/download`

Если документ готов, endpoint возвращает файл.

Если документ еще не готов, endpoint возвращает понятную ошибку, например `409 Conflict`.

### Проверка состояния сервиса

`GET /health`

```json
{
  "status": "ok"
}
```

## 4. Стек

Для внутреннего MVP достаточно легкой инфраструктуры:

- API: FastAPI.
- Язык backend: Python.
- Валидация данных: Pydantic.
- База данных: SQLite с WAL для MVP.
- Production DB позже: PostgreSQL.
- ORM и миграции: SQLAlchemy + Alembic.
- Очередь: таблица `jobs` в SQLite/PostgreSQL.
- Worker: простой worker-loop внутри отдельного процесса или отдельного entrypoint.
- Параллельность: worker-пул с лимитом, например 2-4 одновременные генерации.
- LLM provider: OpenRouter.
- Renderer runtime для `.docx`: Python + python-docx внутри Docker image.
- Sandbox: Docker container.
- Storage: локальная папка `storage/artifacts`, позже S3/MinIO при необходимости.
- Минимальный UI: статическая страница или легкий server-rendered шаблон внутри FastAPI.
- Тестовое развертывание: Docker Compose для API, worker, базы и sandbox runtime.
- Тесты: pytest.

Kafka, RabbitMQ и Celery для внутреннего MVP не нужны. Их можно рассмотреть позже, если появятся высокая нагрузка, несколько backend-инстансов или сложная маршрутизация задач.

## 5. Архитектура

```text
External Client / Minimal Test UI
      |
      v
FastAPI Backend
      |
      +--> Request Validation
      +--> GenerationRequest Repository
      +--> Artifact Repository
      +--> Job Repository
      |
      v
202 Accepted + document_id


Worker Pool
      |
      +--> Job Lease / Status Update
      +--> Generation Pipeline
      |       |
      |       +--> Research / Planning LLM
      |       +--> document_spec.json
      |       +--> content_markdown
      |       +--> Codegen LLM
      |       +--> Docker Sandbox
      |       +--> DOCX Validator
      |       +--> Repair Retry
      |
      +--> Artifact Storage
      +--> Final Status Update
```

Разделение ролей:

- API отвечает за быстрый прием запроса, валидацию, создание job и выдачу статуса.
- Worker отвечает за долгую генерацию.
- Pipeline отвечает за шаги генерации.
- Sandbox отвечает за безопасное исполнение кода.
- Storage отвечает за сохранение готовых файлов.

Текущий синхронный pipeline остается рабочим прототипом до перехода на job-based backend. После перехода `GenerationService` должен создавать job, а не выполнять генерацию внутри HTTP-запроса.

## 6. Очередь jobs и worker-пул

### Jobs table

Для MVP очередь реализуется таблицей `jobs`.

Базовые поля:

- `id`;
- `document_id`;
- `request_id`;
- `status`;
- `priority`;
- `attempts`;
- `max_attempts`;
- `locked_by`;
- `locked_at`;
- `started_at`;
- `finished_at`;
- `last_error`;
- `created_at`;
- `updated_at`.

Статусы job:

- `queued` - задача создана и ждет worker;
- `processing` - worker взял задачу в работу;
- `ready` - документ успешно создан;
- `failed` - задача завершилась ошибкой;
- `canceled` - задача отменена, если позже понадобится отмена.

Внутренний текущий шаг можно хранить отдельно в `current_stage`:

- `planning`;
- `codegen`;
- `sandbox_execution`;
- `validation`;
- `repair`;
- `storage`.

### Worker loop

Worker должен:

1. Забрать из БД несколько `queued` задач с учетом лимита параллельности.
2. Пометить задачу как `processing`.
3. Запустить generation pipeline.
4. Обновлять `current_stage`.
5. На успехе сохранить файл и поставить `ready`.
6. На ошибке выполнить repair retry, если он допустим.
7. После исчерпания попыток поставить `failed`.

Параллельность ограничивается настройкой, например:

```text
WORKER_CONCURRENCY=2
JOB_MAX_ATTEMPTS=3
SANDBOX_TIMEOUT_SECONDS=60
```

Для локального MVP worker может жить в том же процессе через startup task, но предпочтительнее быстро прийти к отдельному процессу:

```text
python -m app.worker
```

Так API и генерация будут разделены яснее.

### Восстановление зависших задач

На старте сервиса или worker нужно подбирать зависшие задачи:

- если job находится в `processing`, но `locked_at` слишком старый, считать ее зависшей;
- если попытки еще остались, вернуть ее в `queued`;
- если попытки исчерпаны, перевести в `failed`;
- сохранить предупреждение или `last_error`, чтобы было понятно, почему задача была восстановлена.

Это защищает от падения процесса посреди генерации.

## 7. Pipeline генерации

Целевой pipeline:

```text
User Prompt
    |
    v
Research / Planning LLM
    |
    v
document_spec.json + content_markdown
    |
    v
Codegen LLM
    |
    v
Python script for python-docx
    |
    v
Docker Sandbox
    |
    v
/output/result.docx
    |
    v
DOCX Validator
    |
    +--> ready
    |
    +--> repair retry -> Codegen LLM -> Sandbox -> Validator
    |
    +--> failed
```

### Research / planning LLM

На этом шаге модель:

- разбирает свободный запрос пользователя;
- определяет формат результата;
- извлекает ограничения;
- дополняет недостающие поля стандартными значениями;
- при необходимости делает research, если выбранная модель и провайдер дают internet access;
- формирует `document_spec.json`;
- готовит `content_markdown`, если контент удобнее описывать Markdown.

Для простых задач можно использовать более дешевую и быструю модель.

### Document spec

`document_spec.json` - главный контракт между planning и codegen.

Пример:

```json
{
  "title": "Коммерческое предложение",
  "language": "ru",
  "document_type": "proposal",
  "style": "business",
  "output_format": "docx",
  "formatting": {
    "page_size": "A4",
    "font": "Times New Roman",
    "font_size": 12
  },
  "content_markdown": "# Заголовок\n\nТекст...",
  "requirements": [
    "Добавить таблицу цен",
    "Добавить блок с контактами"
  ]
}
```

JSON лучше использовать для структуры: секции, таблицы, требования, формат, стиль, ограничения.

Markdown лучше использовать для текстового содержания: заголовки, абзацы, списки, черновой текст.

Оптимальная схема для MVP: сначала строим `document_spec.json`, а внутри него храним `content_markdown`.

### Codegen LLM

На этом шаге модель пишет Python-код под `python-docx`.

Для codegen лучше использовать более сильную модель, потому что стабильность важнее экономии. Долгий thinking не обязателен. Важнее дать четкую инструкцию, короткие примеры кода и строгий контракт:

```text
Создай файл /output/result.docx.
Не читай env.
Не используй network.
Работай только с файлами из /input и /output.
Если нужны данные, бери их из /input/document_spec.json.
```

Codegen prompt должен требовать только код, без пояснений вокруг.

### Repair retry

Если код упал или validator не принял файл, запускается repair prompt.

В repair prompt передается:

- исходный `document_spec.json`;
- предыдущий Python-код;
- traceback;
- ошибки validator-а;
- жесткое требование исправить только код.

Количество repair-попыток ограничивается, например 1-2.

## 8. Sandbox

Код от LLM нельзя запускать на сервере напрямую.

Исполнение должно происходить только внутри Docker container.

Требования к sandbox:

- без доступа к env и secrets backend-а;
- желательно без network на этапе исполнения кода;
- ограничить CPU;
- ограничить RAM;
- ограничить timeout;
- монтировать только `/input` и `/output`;
- `/input` доступен только для чтения;
- `/output` доступен для записи;
- после выполнения проверять, что появился `/output/result.docx`;
- не принимать от контейнера произвольные пути к файлам.

Минимальный runtime container для `.docx`:

- Python;
- python-docx;
- только нужные системные зависимости;
- entrypoint, который запускает сгенерированный скрипт.

Важно: OpenRouter API key и другие secrets не должны попадать внутрь sandbox-контейнера.

## 9. Валидация `.docx`

Validator должен проверять:

- файл существует;
- файл не пустой;
- расширение `.docx`;
- файл открывается через `python-docx`;
- в документе есть хотя бы один параграф или таблица;
- размер файла находится в разумных пределах;
- при необходимости: базовые свойства страницы, шрифты, наличие обязательных секций.

Если validator находит проблему, pipeline запускает repair retry или переводит job в `failed`.

## 10. Подход к форматам

Прототип создает `.docx`, но ядро проекта должно работать с абстрактной спецификацией результата.

Уровни описания:

1. `GenerationSpec` - что хочет пользователь и какие ограничения нужно применить.
2. `DocumentSpec` - нормализованный JSON-контракт для конкретной генерации.
3. `content_markdown` - текстовое содержимое внутри `DocumentSpec`.
4. `Artifact` - итоговый файл и его metadata.

Для будущих форматов:

- `.pptx`: `presentation_spec.json`, возможно images/research assets, runtime с python-pptx;
- `.xlsx`: `workbook_spec.json`, runtime с openpyxl или XlsxWriter;
- `.pdf`: HTML/CSS spec -> PDF renderer или отдельный PDF runtime;
- `.html`: Jinja2 templates + sanitizer.

Для форматов с изображениями понадобится отдельный asset pipeline:

- image search или image generation;
- сохранение источника и лицензии, если используется внешний поиск;
- скачивание/нормализация картинок;
- проверка размера и формата;
- передача изображений в sandbox через `/input/assets`;
- запрет sandbox-у самому ходить в интернет.

## 11. Основные сущности

### GenerationRequest

Хранит входной API-запрос.

Поля:

- `id`;
- `prompt`;
- `requested_output_format`;
- `overrides`;
- `metadata`;
- `created_at`.

### DocumentJob

Хранит задачу фоновой генерации.

Поля:

- `id`;
- `document_id`;
- `request_id`;
- `status`;
- `current_stage`;
- `priority`;
- `attempts`;
- `max_attempts`;
- `locked_by`;
- `locked_at`;
- `started_at`;
- `finished_at`;
- `last_error`;
- `created_at`;
- `updated_at`.

### Artifact

Хранит результат генерации.

Поля:

- `id`;
- `request_id`;
- `job_id`;
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
- `job_id`;
- `stage`;
- `provider`;
- `model`;
- `prompt_version`;
- `input_payload`;
- `raw_output`;
- `parsed_output`;
- `error_message`;
- `created_at`.

### SandboxRun

Хранит результат запуска Docker sandbox.

Поля:

- `id`;
- `job_id`;
- `attempt`;
- `image`;
- `command`;
- `exit_code`;
- `stdout`;
- `stderr`;
- `timeout`;
- `created_at`.

## 12. Конфигурация окружения

Минимальный `.env.example`:

```text
APP_ENV=local
APP_HOST=0.0.0.0
APP_PORT=8000

DATABASE_URL=sqlite:///./storage/app.db
SQLITE_WAL_ENABLED=true

ARTIFACT_STORAGE_PATH=./storage/artifacts

OPENROUTER_API_KEY=
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_PLANNING_MODEL=
OPENROUTER_CODEGEN_MODEL=
OPENROUTER_REPAIR_MODEL=
OPENROUTER_TIMEOUT_SECONDS=60

DEFAULT_OUTPUT_FORMAT=docx
DEFAULT_LANGUAGE=ru
DEFAULT_STYLE=business
DEFAULT_TONE=neutral
DEFAULT_FONT_FAMILY=Times New Roman
DEFAULT_FONT_SIZE=12

WORKER_CONCURRENCY=2
JOB_MAX_ATTEMPTS=3
JOB_STALE_AFTER_SECONDS=900

SANDBOX_DOCKER_IMAGE=text-to-doc-docx-runtime:local
SANDBOX_NETWORK=none
SANDBOX_TIMEOUT_SECONDS=60
SANDBOX_MEMORY_LIMIT=512m
SANDBOX_CPU_LIMIT=1

PUBLIC_BASE_URL=http://localhost:8000
API_INTERNAL_TOKEN=
TEST_UI_ENABLED=true
TEST_UI_REQUIRE_TOKEN=true
```

## 13. Тестовое развертывание и минимальный UI

Для ручной проверки сервиса нужен минималистичный UI на своем сервере. Это не продуктовый frontend, а внутренняя тестовая панель.

Задачи UI:

- отправить `POST /documents`;
- показать `document_id`;
- автоматически опрашивать `GET /documents/{document_id}`;
- показывать статусы `queued`, `processing`, `ready`, `failed`;
- показывать текущий этап, если backend его отдает;
- показать ошибку и warnings;
- дать кнопку скачивания, когда появился `download_url`.

Минимальный экран:

- textarea для `prompt`;
- необязательное поле для `overrides` в JSON;
- кнопка создания документа;
- блок статуса;
- блок ошибок;
- кнопка скачивания готового файла.

UI не должен становиться обязательным клиентом. Основной контракт сервиса остается REST API.

Варианты реализации:

- самый простой: `GET /ui` отдает статический HTML + vanilla JS;
- чуть аккуратнее: папка `app/static` и `app/templates`;
- позже при необходимости: отдельный frontend-проект.

Для текущего проекта лучше начать с `GET /ui`, потому что это быстрее для тестирования и не добавляет лишний frontend-стек.

Тестовое развертывание на своем сервере:

- API запускается как отдельный процесс/container;
- worker запускается как отдельный процесс/container;
- SQLite можно оставить для MVP, но включить WAL;
- `storage/artifacts` должен быть persistent volume;
- sandbox runtime должен запускаться через Docker;
- UI доступен только для внутреннего использования;
- доступ к API/UI лучше закрыть внутренним токеном или basic auth на уровне reverse proxy.

Минимальная схема:

```text
Browser
   |
   v
Minimal Test UI
   |
   v
FastAPI API
   |
   +--> SQLite / Postgres
   +--> storage/artifacts
   +--> Worker
           |
           +--> OpenRouter
           +--> Docker Sandbox
```

## 14. Этапы разработки

### Этап 1. Каркас backend - выполнено

Уже есть в коде:

- FastAPI-приложение;
- общий API router;
- `GET /`;
- `GET /health`;
- конфигурация через `.env`;
- базовое логирование;
- структура `app/api`, `app/core`, `app/db`, `app/schemas`, `app/services`, `app/llm`, `app/renderers`, `app/repositories`;
- unit-тесты для health endpoints.

### Этап 2. Синхронный API создания документа - выполнено

Уже есть в коде:

- `POST /documents`;
- `GET /documents/{document_id}`;
- `GET /documents/{document_id}/download`;
- Pydantic-схемы запроса и ответа;
- optional internal token dependency;
- сохранение входного запроса в SQLite;
- создание artifact;
- статусы `processing`, `ready`, `failed`;
- понятная ошибка `409 Conflict`, если файл еще не готов к скачиванию.

Текущий контракт: `POST /documents` пока синхронно выполняет генерацию и возвращает `201 Created`.

### Этап 3. LLM-парсинг, дефолты и OpenRouter - выполнено

Уже есть в коде:

- `GenerationSpec`;
- `ArtifactPlan`;
- `DefaultsResolver`;
- `PromptBuilder`;
- `OpenRouterClient`;
- `LLMRequestParser`;
- `LLMArtifactPlanner`;
- `LLMResponseValidator`;
- fallback-планирование при проблемах LLM;
- сохранение LLM-вызовов;
- автоматическое определение будущего формата из свободного prompt, например `pptx` для запроса "сделай презентацию".

### Этап 4. Генерация `.docx` - выполнено

Уже есть в коде:

- `RendererRegistry`;
- `BaseRenderer`;
- `DocxRenderer`;
- сохранение `.docx` в `storage/artifacts`;
- download endpoint;
- обновление artifact на `ready` или `failed`;
- unit-тесты pipeline и скачивания файла.

### Этап 5. Сквозной синхронный прототип - выполнено

Текущая рабочая baseline-версия:

- клиент отправляет `POST /documents`;
- backend вызывает OpenRouter или fallback;
- backend строит план документа;
- backend создает `.docx`;
- backend возвращает `document_id`, статус, имя файла и `download_url`;
- готовый файл можно скачать через `GET /documents/{document_id}/download`.

Этот этап полезен для проверки идеи, но не является целевой архитектурой. Его важно сохранить как стабильную baseline-версию до миграции на jobs.

### Этап 6. Подготовка к новым форматам - выполнено

Уже есть в коде и документации:

- enum форматов: `docx`, `pptx`, `xlsx`, `pdf`, `html`;
- `SUPPORTED_RENDER_FORMATS`, где сейчас реально поддержан только `docx`;
- нормализация формата;
- определение формата из prompt;
- понятная ошибка для формата, под который еще нет renderer-а;
- тесты выбора renderer-а;
- документация по будущим renderer-ам.

### Этап 7. Минимальный UI для ручного тестирования - выполнено

Цель: быстро тестировать текущую baseline-версию без Swagger и curl.

Уже есть в коде:

- `GET /ui`;
- минимальный HTML + CSS + vanilla JS без отдельного frontend-стека;
- textarea для `prompt`;
- необязательное поле `overrides` в JSON;
- поле `API token` для защищенного API-режима;
- кнопка отправки запроса;
- отправка запроса в текущий `POST /documents`;
- отображение `document_id`, `request_id`, `status`, `output_format`;
- отображение `warnings` и `error_message`;
- скачивание готового файла через кнопку с учетом `X-API-Token`;
- polling-заготовка для будущих статусов `queued` и `processing`;
- unit-тест на доступность UI.

Важно: UI остается внутренним тестовым инструментом. Основной продуктовый контракт - REST API.

### Этап 8. Тестовое развертывание на своем сервере - выполнено

Цель: получить реальный стенд, где можно проверять генерацию вне локальной машины.

Уже есть в коде:

- `Dockerfile` для API;
- `.dockerignore`;
- `docker-compose.yml` для тестового окружения;
- `.env.server.example`;
- проброс `.env` без попадания secrets в git;
- persistent Docker volume для `/app/storage`;
- SQLite для MVP;
- инструкция запуска и обновления в `docs/deploy-vdsina.md`;
- команды проверки `GET /health` и `GET /ui`;
- рекомендация закрыть UI/API через `API_INTERNAL_TOKEN` или reverse proxy auth.

На этом этапе worker еще не обязателен: можно развернуть текущую синхронную baseline-версию.

### Этап 9. Job-based async backend - выполнено

Цель: перейти от синхронного `POST /documents` к целевой схеме `202 Accepted + status polling`.

Нужно сделать:

- добавить модель `DocumentJob`;
- добавить repository для jobs;
- добавить статусы `queued`, `processing`, `ready`, `failed`, `canceled`;
- добавить `current_stage`;
- изменить `POST /documents`: создавать request, artifact и job, затем возвращать `202 Accepted`;
- сохранить внешний `document_id` как главный id для polling и download;
- перенести запуск текущего `GenerationPipeline` из HTTP-запроса в worker;
- добавить `app.worker` или отдельный worker entrypoint;
- ограничить параллельность через `WORKER_CONCURRENCY`;
- добавить восстановление зависших `processing` jobs на старте;
- обновить `GET /documents/{document_id}` так, чтобы он показывал статус job и artifact;
- обновить тесты API под новый контракт.

Ключевой принцип: текущий `GenerationPipeline` не переписывать с нуля, а переиспользовать за worker seam.

### Этап 10. `document_spec.json` и Markdown-контент - выполнено

Цель: подготовить контракт, который позже сможет кормить codegen LLM и разные runtime.

Нужно сделать:

- ввести `DocumentSpec` как отдельную Pydantic-схему;
- добавить `content_markdown`;
- отделить `GenerationSpec` от конкретной runtime-спецификации;
- обновить planning prompt под `document_spec.json`;
- сохранять spec как диагностируемый JSON;
- добавить тесты валидации `DocumentSpec`;
- временно адаптировать `DocxRenderer` так, чтобы он мог строить `.docx` из `DocumentSpec` без Docker/codegen.

### Этап 11. LLM codegen и Docker sandbox для `.docx` - выполнено

Цель: перейти от backend-renderer-а к безопасному исполнению кода, который пишет LLM.

Нужно сделать:

- добавить отдельный codegen prompt;
- добавить строгий contract: создать `/output/result.docx`;
- добавить Docker image для `.docx` runtime;
- запускать LLM-generated Python-код только в sandbox;
- монтировать `/input` и `/output`;
- передавать в `/input/document_spec.json`;
- запретить network и env/secrets внутри sandbox;
- ограничить CPU, RAM и timeout;
- проверять появление `/output/result.docx`;
- сохранять stdout/stderr и exit code.

### Этап 12. Validator и repair retry - выполнено

Цель: сделать генерацию устойчивой к ошибкам codegen и плохим `.docx`.

Нужно сделать:

- добавить `DocxValidator`;
- проверять, что `.docx` открывается через `python-docx`;
- проверять, что документ не пустой;
- проверять базовые обязательные элементы из `DocumentSpec`;
- добавить repair prompt;
- передавать в repair `document_spec.json`, предыдущий код, traceback и ошибки validator-а;
- ограничить repair 1-2 попытками;
- после исчерпания попыток использовать fallback-renderer или переводить job в `failed`, если fallback отключен.

### Этап 13. Новые форматы и assets

Цель: расширить архитектуру за пределы `.docx`.

Нужно сделать:

- спроектировать `presentation_spec.json` для `.pptx`;
- спроектировать `workbook_spec.json` для `.xlsx`;
- спроектировать HTML/CSS pipeline для `.pdf`;
- добавить asset pipeline для изображений;
- сохранять источники изображений и metadata;
- передавать assets в sandbox только через `/input/assets`;
- добавить отдельные validators и runtime images для новых форматов.

### Этап 14. Production-подготовка

Цель: подготовить сервис к более надежной эксплуатации.

Нужно сделать:

- перейти на PostgreSQL, если SQLite перестанет хватать;
- добавить полноценные миграции Alembic;
- разделить docker-compose на локальный, тестовый и production-like варианты;
- добавить внешнее файловое хранилище при необходимости;
- добавить структурированное логирование;
- добавить мониторинг ошибок;
- добавить rate limiting;
- добавить webhook/callback при необходимости;
- добавить backup/retention policy для artifacts и jobs.

## 15. Риски и решения

### Долгая генерация

Риск: OpenRouter, codegen, Docker sandbox и validation могут занимать слишком долго для синхронного HTTP-запроса.

Решение:

- `POST /documents` только создает job;
- генерация идет в worker;
- клиент использует polling через `GET /documents/{document_id}`;
- готовый файл скачивается отдельно.

### Перегрузка OpenRouter или Docker

Риск: слишком много одновременных задач может привести к лимитам OpenRouter, высокой нагрузке CPU/RAM и нестабильности Docker.

Решение:

- `WORKER_CONCURRENCY`;
- лимиты CPU/RAM/timeout для sandbox;
- max attempts;
- понятный статус `failed`;
- сохранение причины ошибки.

### Зависшие задачи

Риск: worker может упасть, когда job уже находится в `processing`.

Решение:

- `locked_at`;
- `locked_by`;
- `JOB_STALE_AFTER_SECONDS`;
- восстановление зависших задач на старте worker;
- возврат в `queued` или перевод в `failed`.

### Нестабильный JSON от LLM

Риск: модель может вернуть текст вместо JSON или нарушить схему.

Решение:

- строгий planning prompt;
- Pydantic-валидация;
- отдельный repair/fix prompt для JSON;
- сохранение сырого ответа модели для диагностики.

### Нестабильный Python-код от LLM

Риск: codegen LLM может написать код, который падает или создает плохой `.docx`.

Решение:

- строгий codegen contract;
- запуск только в Docker sandbox;
- сохранение traceback;
- `DocxValidator`;
- 1-2 repair retry;
- отказ после исчерпания попыток.

### Безопасность sandbox

Риск: LLM-generated code может попытаться читать env, ходить в network или писать за пределы рабочей папки.

Решение:

- не запускать код на backend-хосте напрямую;
- Docker container без secrets;
- network disabled;
- CPU/RAM/timeout limits;
- монтировать только `/input` и `/output`;
- принимать только `/output/result.docx`.

### Расширение форматов

Риск: если `.docx`-логика попадет в общий pipeline, будущие `.pptx`, `.xlsx` и `.pdf` будет сложно добавить.

Решение:

- общий job lifecycle;
- форматные spec-контракты;
- отдельные runtime images;
- отдельные validators;
- общий интерфейс storage/status, но разные renderer/codegen adapters.

## 16. Принципы проекта

- Backend является самостоятельным API-сервисом.
- API не должен блокироваться долгой генерацией.
- `POST /documents` создает job и возвращает `202 Accepted`.
- Worker выполняет generation pipeline в фоне.
- Прототип создает `.docx`, но ядро проектируется под разные форматы.
- Пользовательский запрос разбирается через LLM, потому что вход будет свободным и разговорным.
- Все недостающие параметры заполняются стандартными значениями.
- OpenRouter используется только через отдельный слой клиента и LLM-сервисов.
- Planning, codegen и repair являются разными LLM-ролями.
- LLM должна возвращать структурированный план или код по строгому contract, а не готовый файл.
- LLM-generated code нельзя запускать напрямую на сервере.
- Sandbox не должен иметь доступ к env/secrets.
- Исходный запрос, ответы LLM, спецификация, sandbox-логи и созданный файл хранятся отдельно.
- Ошибки должны быть видны через API и сохранены для диагностики.
- Локальная разработка должна запускаться понятными командами для API и worker.

## 17. Что делаем следующим практическим шагом

Текущая версия уже прошла этапы 1-11: есть тестовый деплой, job-based backend, polling UI, `document_spec.json`, LLM codegen для `.docx` и Docker sandbox с fallback-renderer.

Следующий практический шаг - этап 13: новые форматы и assets.

Практический порядок для будущей реализации:

1. Спроектировать `presentation_spec.json` для `.pptx`.
2. Спроектировать `workbook_spec.json` для `.xlsx`.
3. Спроектировать HTML/CSS pipeline для `.pdf`.
4. Добавить asset pipeline для изображений.
5. Сохранять источники изображений и metadata.
6. Передавать assets в sandbox только через `/input/assets`.
7. Добавить отдельные validators и runtime images для новых форматов.
