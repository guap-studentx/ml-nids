# ML-NIDS

ML-NIDS — система для ВКР по теме **Выявления аномалий в сетевом трафике методами машинного обучения**. 

Система поддерживает offline-анализ CSV и PCAP, live-захват через агент на хосте, непрерывный live-мониторинг по chunks, реестр моделей, аналитику просмотр flow, экспорт CSV и генерацию PDF/HTML отчётов.

## Архитектура

- `backend/` — FastAPI API, модели PostgreSQL, миграции Alembic, inference,
  жизненный цикл captures/live sessions, отчёты.
- `frontend/` — React + Tailwind UI, в Docker отдаётся через nginx.
- `agent/` — хостовый `livecap-agent`; запускается на машине или VM, где видны
  нужные сетевые интерфейсы. В Docker агент не запускается.
- `artifacts/` — исследовательские артефакты: препроцессор, 8 моделей,
  manifest и конфигурация признаков.
- `docker-compose.yml` — PostgreSQL, backend, frontend.

## Требования

- Docker Desktop (для Windows/MacOS) / Docker.
- `uv` для локальных Python-команд и запуска агента.
- Wireshark с Npcap на Windows или `dumpcap`/`tshark`/`tcpdump` на Linux для
  live-захвата.
- В `artifacts/` должны быть `model_registry_manifest.json`,
  `preprocessor.joblib`, `feature_names.json` и файлы моделей `.joblib`.

## Быстрый запуск

Из корня репозитория:

```powershell
docker compose --env-file .env.example up -d --build
```

Сервисы:

- frontend: `http://localhost:5173`
- backend API: `http://localhost:8000`
- Swagger/OpenAPI: `http://localhost:8000/docs`

Логин по умолчанию из `.env.example`:

- пользователь: `admin`
- пароль: `admin`

При старте backend применяет миграции, создаёт admin-пользователя и загружает
все модели из `/models`, который монтируется из локальной папки `artifacts/`.

## Частые команды

Пересобрать только backend после изменений:

```powershell
docker compose --env-file .env.example build backend
docker compose --env-file .env.example up -d --no-deps backend
```

Пересобрать только frontend после изменений:

```powershell
docker compose --env-file .env.example build frontend
docker compose --env-file .env.example up -d --no-deps frontend
```

Запустить backend-тесты локально:

```powershell
cd backend
uv run pytest
```

Проверить frontend локально:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

## Offline-анализ

Откройте страницу `Captures`.

- `Offline CSV analysis` — загрузка готовой таблицы flow в формате,
  совместимом с NFStream.
- `Offline PCAP analysis` — загрузка `.pcap` или `.pcapng`.
- После выбора активной модели анализ запускается в backend.
- Completed capture можно открыть для просмотра summary, score distribution,
  top endpoints, anomaly flows, экспорта CSV и генерации отчёта.

## Live-захват и непрерывный мониторинг

1. Откройте `Agents`.
2. Создайте агента и сохраните одноразовый token.
3. Запустите агента на машине или VM, где виден нужный интерфейс:

```powershell
uv run --project agent livecap-agent --backend-url http://localhost:8000 --agent-id <agent-id> --token <token> --interval 5
```

Можно один раз сохранить параметры в конфиг:

```powershell
uv run --project agent livecap-agent --config agent/config.json --backend-url http://localhost:8000 --agent-id <agent-id> --token <token> --interval 5 --write-config
uv run --project agent livecap-agent --config agent/config.json
```

На Windows агент ищет `dumpcap` в `PATH` и в
`C:\Program Files\Wireshark\dumpcap.exe`. На Ubuntu установите инструменты:

```bash
sudo apt update
sudo apt install -y tshark tcpdump
```

4. Дождитесь статуса агента `online`.
5. Для разового live-захвата откройте `Captures` и выберите `Live capture`.
6. Для непрерывного анализа откройте `Live Monitor`, задайте agent/interface,
   модель, длительность и размер chunk.

В bounded live capture агент записывает одно PCAP-окно и отправляет его в
backend. В continuous live monitoring агент пишет rolling PCAP chunks, каждый
chunk отправляется в backend и анализируется тем же PCAP inference pipeline.

## Модели

Страница `Models` позволяет:

- просматривать все зарегистрированные модели;
- включать/выключать модель;
- назначать default-модель;
- удалять неиспользуемые модели;
- загружать новый `.joblib`-артефакт в формате исследовательского контракта;
- открывать подробности: test/train metrics, architecture config, размер,
  время обучения/предсказания и feature importance.

## Отчёты

Отчёты создаются для completed captures.

- В `CaptureDetail` нажмите `Report`.
- На странице `Reports` можно скачать созданный PDF.

PDF/HTML отчёты содержат шапку capture, KPI, top sources/destinations, score
distribution и таблицу последних anomaly flows.

## Статус проекта

Реализовано:

- авторизация и инициализация admin-пользователя;
- загрузка 8 исследовательских моделей из `artifacts/`;
- загрузка новых model artifacts через UI/API;
- details-модалка моделей с метриками и feature importance;
- offline CSV и PCAP analysis;
- bounded live capture через хостовый агент;
- continuous live monitoring через live sessions и rolling chunks;
- страница `Live Monitor`;
- история captures, аналитика, просмотр flow, экспорт CSV;
- WebSocket-обновления прогресса на странице активного capture;
- стилизованные PDF/HTML отчёты;
- страницы Dashboard, Models, Agents, Captures, History, Reports;
- Docker Compose развёртывание.

Не реализовано или оставлено как улучшение:

- управление агентом через WebSocket; сейчас агент использует HTTP polling;
- лабораторные attack scripts и отдельный `evaluate_capture.py`.

## Полезные пути

- Экспорты flow сохраняются в Docker volume `captures_volume`.
- Загруженные входные файлы сохраняются в `uploads_volume`.
- Сгенерированные отчёты сохраняются в `reports_volume`.
- Локальные PCAP-файлы агента используют `.livecap-agent/` по умолчанию.
  После загрузки PCAP удаляются, если агент не запущен с `keep_pcaps` /
  `--keep-pcaps`.
