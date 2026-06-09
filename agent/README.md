# livecap-agent

`livecap-agent` — хостовый агент ML-NIDS для захвата трафика. Его нужно
запускать на машине или виртуальной машине, где видны нужные сетевые
интерфейсы. В Docker агент не запускается.

## Запуск

Сначала создайте агента в web-интерфейсе на странице `Agents`. После создания
сохраните `id` и одноразовый token.

```powershell
uv run --project agent livecap-agent --agent-id <agent-id> --token <token>
```

Полезные варианты:

```powershell
uv run --project agent livecap-agent --agent-id <agent-id> --token <token> --once
uv run --project agent livecap-agent --backend-url http://localhost:8000 --agent-id <agent-id> --token <token> --interval 5
```

## Конфигурационный файл

Чтобы не вводить длинную команду каждый раз, сохраните параметры подключения
один раз:

```powershell
uv run --project agent livecap-agent --config agent/config.json --backend-url http://localhost:8000 --agent-id <agent-id> --token <token> --interval 5 --write-config
```

Дальше агент можно запускать так:

```powershell
uv run --project agent livecap-agent --config agent/config.json
```

Формат конфига:

```json
{
  "backend_url": "http://localhost:8000",
  "agent_id": "<agent-id>",
  "token": "<token>",
  "interval_seconds": 5,
  "capture_mode": "pcap",
  "work_dir": ".livecap-agent",
  "keep_pcaps": false,
  "max_pcap_files": 100,
  "pcap_retention_hours": 24
}
```

CLI-аргументы имеют приоритет над значениями из файла. `agent/config.json`
игнорируется git, так как содержит agent token.

## Режим захвата

Параметр `capture_mode` управляет тем, что агент отправляет в backend:

- `pcap` — режим по умолчанию. Агент пишет PCAP/PCAPNG внешним инструментом
  `dumpcap`, `tshark` или `tcpdump`, а backend извлекает flows через NFStream.
- `flows` — агент использует NFStream напрямую на сетевом интерфейсе и
  отправляет в backend CSV с flow-признаками. Промежуточный PCAP-файл в этом
  режиме не создаётся.

Режим можно выбрать в конфиге:

```json
"capture_mode": "flows"
```

или через CLI:

```powershell
uv run --project agent livecap-agent --config agent/config.json --capture-mode flows
```

В режиме `flows` на машине агента должны быть доступны зависимости NFStream.
В этом режиме chunk завершается по таймеру агента, а NFStream отдаёт только
истёкшие flows. Для длинных активных соединений возможна нарезка по
`active_timeout`.

Практически режим `flows` рекомендуется запускать на Linux-сенсоре. На Windows
NFStream может требовать дополнительные native-библиотеки, поэтому для Windows
остаётся предпочтительным режим `pcap` через Wireshark `dumpcap`.

## Хранение PCAP/CSV

По умолчанию агент удаляет локальный PCAP или CSV после успешной загрузки в
backend. Для отладки можно включить:

```json
"keep_pcaps": true
```

или запустить агент с `--keep-pcaps`. Даже в этом режиме агент выполняет
очистку старых файлов по параметрам `max_pcap_files` и `pcap_retention_hours`.

## Инструменты захвата

Для live capture нужен один из инструментов:

- Windows: Wireshark `dumpcap` + Npcap.
- Linux: `dumpcap`, `tshark` или `tcpdump`.

На Ubuntu:

```bash
sudo apt update
sudo apt install -y tshark tcpdump
```

На Linux вывод `tcpdump` передаётся через процесс агента, чтобы избежать
ограничений записи в рабочую директорию со стороны tcpdump/AppArmor.

## Режимы работы

Агент понимает два типа команд от backend:

- bounded capture — один PCAP-захват заданной длительности;
- continuous live session — rolling capture, где трафик режется на chunks,
  каждый chunk загружается в backend и анализируется отдельно.

Continuous session завершается по истечении duration или после перевода сессии
в `stopping` со стороны backend.

## Переменные окружения

Те же параметры можно передать через env:

```powershell
$env:ML_NIDS_BACKEND_URL="http://localhost:8000"
$env:ML_NIDS_AGENT_ID="<agent-id>"
$env:ML_NIDS_AGENT_TOKEN="<token>"
uv run --project agent livecap-agent
```
