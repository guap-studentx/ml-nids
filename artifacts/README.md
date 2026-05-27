# Артефакты проекта NFS-2023-nTE для бинарного выявления аномалий

Сгенерировано: 2026-05-19T15:18:50

## Состав

| Файл | Назначение |
|------|-----------|
| `preprocessor.joblib` | sklearn ColumnTransformer (log1p + RobustScaler + passthrough) |
| `preprocessing_config.json` | Метаданные препроцессинга (список фичей, параметры) |
| `feature_names.json` | 42 имени признаков в каноническом порядке |
| `split_meta.json` | Параметры train/test split (random_state, test_size, размеры) |
| `model_registry_manifest.json` | **Главный реестр** — описание всех моделей |
| `architectures.py` | Самодостаточные классы нейросетей (нужны для AE, MLP, FT) |
| `metrics.py` | Функция compute_binary_metrics для оценки |
| `model_*.joblib` | Артефакты моделей в формате исследовательского контракта |

## Контракт на входные данные

Все модели принимают **42 признака** в каноническом порядке (см.
`feature_names.json`). Перед подачей в модель данные должны быть
препроцессированы через `preprocessor.joblib`.

## Шаблон inference на новых данных

### 1. Препроцессинг (одинаковый для всех моделей)

```python
import joblib, pandas as pd, json

pp = joblib.load("preprocessor.joblib")
with open("feature_names.json") as f:
    feature_names = json.load(f)["feature_names"]

# X_raw — DataFrame с 42 колонками (имена точно по feature_names)
X_pp = pp.transform(X_raw)[feature_names]   # 42 колонки в каноническом порядке
```

### 2. Sklearn-модели: RF, XGBoost, LightGBM, DecisionTree, GaussianNB

```python
art = joblib.load("model_xgboost.joblib")    # любой sklearn-модельный артефакт
model = art["model"]
proba = model.predict_proba(X_pp.values)[:, 1]
pred  = (proba >= art["decision_threshold"]).astype(int)
```

### 3. Нейросети MLP и FT-Transformer

```python
import torch
from architectures import TabularMLP   # или TabularFTTransformer

art = joblib.load("model_mlp.joblib")
ModelCls = TabularMLP    # либо TabularFTTransformer, согласно art['model_class_name']
model = ModelCls(**art["model_config"])
model.load_state_dict(art["state_dict"])
model.eval()
with torch.no_grad():
    x = torch.from_numpy(X_pp.values.astype('float32'))
    proba = torch.sigmoid(model(x)).numpy().ravel()
pred = (proba >= art["decision_threshold"]).astype(int)
```

### 4. Autoencoder (one-class)

```python
import torch
from architectures import TabularAutoencoder

art = joblib.load("model_autoencoder.joblib")
model = TabularAutoencoder(**art["model_config"])
model.load_state_dict(art["state_dict"])
model.eval()
with torch.no_grad():
    x = torch.from_numpy(X_pp.values.astype('float32'))
    recon = model(x)
    recon_err = ((recon - x) ** 2).mean(dim=1).numpy()
pred = (recon_err > art["decision_threshold"]).astype(int)
```

## Рекомендации по выбору модели

| Сценарий | Рекомендованная модель | Аргументы |
|----------|------------------------|-----------|
| Основной detector для эксплуатации | **XGBoost** | F1=0.99880, обучение 1.2с на GPU, 80 KB, throughput 2.5M flow/sec |
| Максимально быстрый inference | **DecisionTree** | F1=0.99860, throughput 13M flow/sec |
| Интерпретируемость через attention | **FT-Transformer** | F1=0.99853, attention-карты для каждого решения |
| Novelty detection без меток | **Autoencoder** | F1=0.74, one-class подход, ловит редкие/новые атаки |
| Гибридная архитектура | XGBoost + AE | Основной detector + дополнительная проверка атипичных атак |

## Источник данных и формат

- Датасет: NFS-2023-nTE (CICIDS-2017 → NFStream offline rebuilt).
- 5 дней, Monday-Friday, 2 111 131 flow, 14 типов атак + BENIGN.
- Признаки: 42 NFStream-агрегата на flow (без IP/port/MAC — без утечки).
- Бинарный target: 0 = BENIGN, 1 = любой тип атаки.

## Структура артефакта

Каждый файл `model_*.joblib` содержит словарь с ключами:
- `model_class_name` — имя класса для восстановления.
- `model_features` — список 42 имён фичей.
- `metrics_test`, `metrics_train` — 12 метрик.
- `score_type` — `"predict_proba"` или `"reconstruction_error"`.
- `decision_threshold` — порог для бинарного предсказания.
- `preprocessor_path` — указатель на `preprocessor.joblib`.
- Для sklearn: `model` — сам объект.
- Для pytorch: `state_dict`, `model_config`, `architecture_module`.
