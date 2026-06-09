import { createContext, useCallback, useContext, useMemo, useState } from "react";

const storageKey = "ml_nids_language";

const translations = {
  ru: {
    "Restore session": "Восстановление сессии",
    Logout: "Выйти",
    Language: "Язык",
    "Traffic analysis": "Анализ трафика",
    Dashboard: "Обзор",
    Captures: "Анализы",
    "Live Monitor": "Live-мониторинг",
    Models: "Модели",
    Agents: "Агенты",
    History: "История",
    Reports: "Отчеты",
    Refresh: "Обновить",
    Back: "Назад",
    "Export CSV": "Экспорт CSV",
    Report: "Отчет",
    Generating: "Генерация",
    "All flows": "Все flow",
    Upload: "Загрузить",
    Uploading: "Загрузка",
    Start: "Запустить",
    Starting: "Запуск",
    Stop: "Остановить",
    Delete: "Удалить",
    View: "Открыть",
    Details: "Детали",
    Close: "Закрыть",
    Apply: "Применить",
    Previous: "Назад",
    Next: "Вперед",
    Download: "Скачать",
    Create: "Создать",
    Creating: "Создание",
    Enable: "Включить",
    Disable: "Отключить",
    Default: "По умолчанию",
    Ifaces: "Интерфейсы",
    All: "Все",
    Anomaly: "Аномалия",
    Benign: "Норма",
    Name: "Имя",
    Mode: "Режим",
    Status: "Статус",
    Flows: "Flow",
    Anomalies: "Аномалии",
    Finished: "Завершено",
    Actions: "Действия",
    Sessions: "Сессии",
    "Anomalies 24h": "Аномалии за 24 ч",
    "Active agents": "Активные агенты",
    "Active models": "Активные модели",
    "Anomaly timeline": "Динамика аномалий",
    hours: "часов",
    "Recent captures": "Последние анализы",
    "No points for selected period.": "Нет точек для выбранного периода.",
    "No capture sessions yet.": "Анализов пока нет.",
    "System summary for processed sessions, anomalies, and component status.":
      "Оперативная сводка по обработанным сессиям, аномалиям и состоянию компонентов.",
    Username: "Логин",
    Password: "Пароль",
    "Sign in": "Войти",
    "Signing in...": "Вход...",
    "Network traffic analysis panel": "Панель анализа сетевого трафика",
    "Offline and live analysis history. Total: {total}.":
      "История offline и live-сессий анализа. Всего: {total}.",
    "Select a {label} file and a model": "Выберите {label}-файл и модель",
    "{label} analysis started. Session ID: {id}": "Анализ {label} запущен. Session ID: {id}",
    "Select a model, online agent, and interface": "Выберите модель, online-агента и интерфейс",
    "Live capture queued. Session ID: {id}": "Live capture поставлен в очередь. Session ID: {id}",
    "Capture {name} deleted": "Capture {name} удален",
    "Stop requested for {name}. Status: {status}": "Stop запрошен для {name}. Статус: {status}",
    "Live capture": "Live-захват",
    "Command to an online agent: capture traffic on a selected interface and analyze it with a model.":
      "Команда online-агенту: захват трафика на выбранном интерфейсе и анализ моделью.",
    "Offline CSV analysis": "Offline-анализ CSV",
    "Upload an NFStream-format flow table for inference with the selected model.":
      "Загрузка flow-таблицы NFStream-формата для инференса выбранной моделью.",
    "Offline PCAP analysis": "Offline-анализ PCAP",
    "Upload PCAP/PCAPNG: backend extracts flows through NFStream using research settings.":
      "Загрузка PCAP/PCAPNG: backend извлечет flow через NFStream с настройками исследовательской части.",
    "Session name": "Имя сессии",
    Model: "Модель",
    Agent: "Агент",
    Interface: "Интерфейс",
    "Duration, sec": "Длительность, сек",
    "BPF filter": "BPF-фильтр",
    "No online agents": "Нет online-агентов",
    "No interfaces": "Нет интерфейсов",
    "For example, lab-portscan-xgboost": "Например, lab-portscan-xgboost",
    "For example, attack-window-01": "Например, attack-window-01",
    "For example, live-office-traffic": "Например, live-office-traffic",
    "For example, tcp port 443": "Например, tcp port 443",
    "No sessions yet.": "Сессий пока нет.",
    "Continuous traffic analysis: the agent sends short PCAP chunks, backend aggregates the result.":
      "Непрерывный анализ трафика: агент отправляет короткие PCAP chunks, backend агрегирует результат.",
    "Start continuous session": "Запуск continuous-сессии",
    "Rolling capture with configured chunk size and total duration.":
      "Rolling capture с заданным размером chunk и общей длительностью.",
    "Chunk, sec": "Chunk, сек",
    "Live session created. ID: {id}": "Live session создана. ID: {id}",
    "Live session {name} deleted": "Live session {name} удалена",
    "No live sessions yet.": "Live sessions пока нет.",
    "Select or start a live session.": "Выберите или запустите live session.",
    Rate: "Доля",
    Chunks: "Chunks",
    Started: "Начато",
    "Recent anomaly chunks": "Последние chunks с аномалиями",
    "No chunks yet.": "Chunks пока нет.",
    Open: "Открыть",
    "No chunks yet. Start the agent so it can receive the command.":
      "Chunks пока нет. Запустите агента, чтобы он получил команду.",
    "Capture detail": "Детали capture",
    "Loading capture data": "Загрузка данных capture-сессии",
    "Total flows": "Всего flow",
    "Anomaly rate": "Доля аномалий",
    "Score distribution": "Распределение score",
    "No distribution data.": "Нет данных для распределения.",
    "Top sources": "Топ источников",
    "Top destinations": "Топ получателей",
    "Recent anomaly flows": "Последние аномальные flow",
    Timestamp: "Время",
    Endpoint: "Endpoint",
    Protocol: "Протокол",
    Packets: "Пакеты",
    Bytes: "Байты",
    Score: "Score",
    Prediction: "Прогноз",
    "No anomaly flows yet.": "Аномальных flow пока нет.",
    Value: "Значение",
    Count: "Количество",
    "No data.": "Нет данных.",
    "Capture flows": "Flow capture",
    "{id} · {total} records": "{id} · {total} записей",
    "Min score": "Мин. score",
    "Source IP": "IP источника",
    "Destination IP": "IP получателя",
    "Duration ms": "Длительность, мс",
    "No flows found.": "Flow не найдены.",
    "Page {page} of {totalPages}": "Страница {page} из {totalPages}",
    "Archive of capture sessions with filters. Total: {total}.":
      "Архив capture-сессий с фильтрами. Всего: {total}.",
    "Date from": "Дата от",
    "Date to": "Дата до",
    "No capture sessions match selected filters.": "Capture-сессий по выбранным фильтрам нет.",
    "Manage livecap-agent sensors: registration, interfaces, and connection state.":
      "Управление livecap-agent: регистрация сенсоров, интерфейсы и состояние подключения.",
    "Agent management is available only to administrators.":
      "Управление агентами доступно только администратору.",
    "Add livecap-agent": "Добавить livecap-agent",
    "Create an agent record and save the token for running it on the sensor host.":
      "Создайте запись агента и сохраните token для запуска на sensor-хосте.",
    "Agent name": "Имя агента",
    "Enter agent name": "Введите имя агента",
    "Agent created. Token is shown only once.": "Агент создан. Token показывается только один раз.",
    "Agent {name} deleted": "Агент {name} удален",
    "Token for {name}": "Token для {name}",
    "Last seen": "Последний heartbeat",
    Interfaces: "Интерфейсы",
    "No agents yet.": "Агентов пока нет.",
    "Registry of trained models loaded from research artifacts.":
      "Реестр обученных моделей, загруженных из артефактов исследовательской части.",
    "Upload model artifact": "Загрузка артефакта модели",
    "Upload a .joblib artifact in the research contract format.":
      "Загрузка `.joblib` артефакта в формате исследовательского контракта.",
    "Model ID": "ID модели",
    "Display name": "Отображаемое имя",
    "Optional display name": "Необязательное имя",
    Artifact: "Артефакт",
    Registered: "Зарегистрировано",
    Active: "Активно",
    Class: "Класс",
    Threshold: "Порог",
    "F1 anomaly": "F1 anomaly",
    State: "Состояние",
    "Model status updated": "Статус модели обновлен",
    "Default model updated": "Default-модель обновлена",
    "Model deleted": "Модель удалена",
    "Select a .joblib model file": "Выберите .joblib файл модели",
    "Model {name} uploaded": "Модель {name} загружена",
    "Score type": "Тип score",
    Features: "Признаки",
    "Size KB": "Размер, KB",
    "Test metrics": "Метрики test",
    "Train metrics": "Метрики train",
    "Model config": "Конфигурация модели",
    "Feature importance": "Важность признаков",
    "Feature importance is not available for this artifact.":
      "Feature importance недоступен для этого артефакта.",
    "Generated analysis reports. Total: {total}.": "Сгенерированные отчеты анализа. Всего: {total}.",
    Capture: "Capture",
    Format: "Формат",
    Created: "Создан",
    "No reports yet.": "Отчетов пока нет.",
    "Flow detail": "Детали flow",
    "Loading flow": "Загрузка flow",
    "Loading...": "Загрузка...",
    "Top numeric deviations": "Главные числовые отклонения",
    Feature: "Признак",
    "No numeric features for explanation.": "Нет числовых признаков для explanation.",
    "Report generated: {id}": "Отчет создан: {id}",
    pending: "ожидает",
    running: "выполняется",
    stopping: "останавливается",
    completed: "завершено",
    failed: "ошибка",
    stopped: "остановлено",
    online: "online",
    offline: "offline",
    busy: "занят",
    active: "активна",
    inactive: "отключена",
    default: "по умолчанию",
    unknown: "неизвестно",
    live: "live",
    offline_csv: "offline CSV",
    offline_pcap: "offline PCAP",
  },
};

const LanguageContext = createContext(null);

function initialLanguage() {
  const stored = localStorage.getItem(storageKey);
  if (stored === "en" || stored === "ru") return stored;
  return navigator.language?.toLowerCase().startsWith("ru") ? "ru" : "en";
}

export function LanguageProvider({ children }) {
  const [language, setLanguageState] = useState(initialLanguage);

  const setLanguage = useCallback((nextLanguage) => {
    const normalized = nextLanguage === "ru" ? "ru" : "en";
    setLanguageState(normalized);
    localStorage.setItem(storageKey, normalized);
  }, []);

  const t = useCallback(
    (key, params = {}) => {
      const translated = translations[language]?.[key] ?? key;
      return Object.entries(params).reduce(
        (text, [name, value]) => text.replaceAll(`{${name}}`, String(value)),
        translated,
      );
    },
    [language],
  );

  const value = useMemo(() => ({ language, setLanguage, t }), [language, setLanguage, t]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const value = useContext(LanguageContext);
  if (!value) {
    throw new Error("useLanguage must be used inside LanguageProvider");
  }
  return value;
}
