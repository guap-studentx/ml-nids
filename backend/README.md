# Backend ML-NIDS

Backend ML-NIDS — FastAPI-приложение. Он отвечает за авторизацию,
реестр моделей, обработку CSV/PCAP, inference, хранение captures/flows,
управление агентами, live sessions и генерацию отчётов.

## Локальная разработка

```powershell
cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Приложение читает настройки из переменных окружения. Пример находится в `.env.example` в корне репозитория.

## Проверки

```powershell
cd backend
uv run pytest
```

## Основные модули

- `app/api/v1/` — REST API и WebSocket endpoints.
- `app/models/` — SQLAlchemy-модели.
- `app/repositories/` — слой доступа к данным.
- `app/services/` — бизнес-логика.
- `app/inference/` — загрузка артефактов и стратегии inference.
- `alembic/versions/` — миграции БД.

## Запуск в Docker

Обычно backend запускается вместе с остальными сервисами из корня проекта:

```powershell
docker compose --env-file .env.example up -d --build
```

При старте контейнер выполняет:

1. `alembic upgrade head`;
2. создание admin-пользователя;
3. загрузку моделей из `/models`;
4. запуск `uvicorn`.

Папка `/models` монтируется из локальной `artifacts/`.
