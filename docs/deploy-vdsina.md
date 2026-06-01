# Тестовое развертывание на VDSina

Инструкция рассчитана на Ubuntu 24.04/22.04, Docker и текущую синхронную baseline-версию проекта.

## 1. Подготовить сервер

Подключиться по SSH:

```bash
ssh root@SERVER_IP
```

Обновить систему:

```bash
apt update && apt upgrade -y
```

Установить Docker и Docker Compose plugin:

```bash
apt install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Проверить:

```bash
docker --version
docker compose version
```

## 2. Загрузить проект

Создать папку:

```bash
mkdir -p /opt/text-to-doc-builder
cd /opt/text-to-doc-builder
```

Загрузить файлы проекта любым удобным способом: через git или архив.

Самый аккуратный вариант без git - собрать архив из нужных файлов на Windows.

В PowerShell из папки проекта:

```powershell
Compress-Archive `
  -Path .\app, .\docs, .\pyproject.toml, .\README.md, .\Dockerfile, .\docker-compose.yml, .\.dockerignore, .\.env.server.example `
  -DestinationPath .\deploy.zip `
  -Force

scp .\deploy.zip root@SERVER_IP:/opt/text-to-doc-builder/deploy.zip
```

На сервере:

```bash
cd /opt/text-to-doc-builder
apt install -y unzip
unzip -o deploy.zip
```

Так на сервер не попадут локальные `.env`, `.venv`, `storage` и кэш-папки.

## 3. Создать `.env` на сервере

На сервере:

```bash
cd /opt/text-to-doc-builder
cp .env.server.example .env
nano .env
```

Заполнить минимум:

```text
OPENROUTER_API_KEY=твой_ключ_openrouter
OPENROUTER_MODEL=выбранная_модель
OPENROUTER_CODEGEN_MODEL=anthropic/claude-sonnet-4.5
PUBLIC_BASE_URL=http://SERVER_IP
API_INTERNAL_TOKEN=любой_секретный_токен_для_UI_и_API
DOCX_VALIDATION_ENABLED=true
DOCX_CODEGEN_REPAIR_ATTEMPTS=1
```

`API_INTERNAL_TOKEN` не является ключом OpenRouter. Это внутренний пароль для доступа к `/documents` из UI или другого клиента.

## 4. Запустить сервис

```bash
docker compose --profile runtime build docx-runtime
docker compose up -d --build
```

Проверить контейнер:

```bash
docker compose ps
docker compose logs -f api
```

## 5. Проверить в браузере

Открыть:

```text
http://SERVER_IP/health
http://SERVER_IP/ui
```

Если задан `API_INTERNAL_TOKEN`, вставить его в поле `API token` в UI.

## 6. Проверить генерацию

В UI отправить prompt:

```text
Сделай краткий документ по итогам встречи
```

Ожидаемый результат:

- статус `ready`;
- `output_format` равен `docx`;
- появляется кнопка скачивания файла.

## 7. Обновить сервис после изменений

На сервере в папке проекта:

```bash
docker compose --profile runtime build docx-runtime
docker compose up -d --build
```

Если нужно посмотреть логи:

```bash
docker compose logs -f api
```

## 8. Остановить сервис

```bash
docker compose down
```

Файлы и SQLite база останутся в Docker volume `text-to-doc-builder_text_to_doc_storage`.

Посмотреть volume:

```bash
docker volume ls
```
