"""
Единая функция для расчёта 12 метрик бинарной классификации.
Используется во всех ноутбуках для модулей оценки.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
)


def compute_binary_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: Optional[np.ndarray] = None,
) -> dict:
    """Считает 12 метрик бинарной классификации.

    Соглашение классов:
      - 0 = BENIGN (negative)
      - 1 = ANOMALY (positive)

    Returns
    -------
    dict с ключами:
      accuracy, precision_anomaly, recall_anomaly, f1_anomaly,
      precision_benign, recall_benign, f1_benign,
      f1_macro, f1_weighted, roc_auc, pr_auc, balanced_accuracy.
    """
    y_true = np.asarray(y_true).ravel()
    y_pred = np.asarray(y_pred).ravel()
    assert y_true.shape == y_pred.shape, \
        f"shape mismatch: {y_true.shape} vs {y_pred.shape}"
    assert set(np.unique(y_pred)).issubset({0, 1}), \
        f"y_pred должен быть бинарным; уникальные: {np.unique(y_pred)}"

    # per-class precision/recall/f1
    p, r, f, _ = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1], zero_division=0
    )

    metrics = {
        "accuracy":            float(accuracy_score(y_true, y_pred)),
        "precision_anomaly":   float(p[1]),
        "recall_anomaly":      float(r[1]),
        "f1_anomaly":          float(f[1]),
        "precision_benign":    float(p[0]),
        "recall_benign":       float(r[0]),
        "f1_benign":           float(f[0]),
        "f1_macro":            float(f1_score(y_true, y_pred, average="macro",
                                              zero_division=0)),
        "f1_weighted":         float(f1_score(y_true, y_pred, average="weighted",
                                              zero_division=0)),
        "balanced_accuracy":   float(balanced_accuracy_score(y_true, y_pred)),
    }

    if y_score is not None:
        y_score = np.asarray(y_score).ravel()
        metrics["roc_auc"] = float(roc_auc_score(y_true, y_score))
        metrics["pr_auc"]  = float(average_precision_score(y_true, y_score))
    else:
        metrics["roc_auc"] = float("nan")
        metrics["pr_auc"]  = float("nan")

    return metrics


def confusion_matrix_dict(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """Возвращает confusion matrix в виде словаря (для JSON-сериализации)."""
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    return {
        "tn": int(cm[0, 0]),  # true negative — BENIGN корректно
        "fp": int(cm[0, 1]),  # false positive — BENIGN ошибочно как ANOMALY
        "fn": int(cm[1, 0]),  # false negative — ANOMALY пропущенный
        "tp": int(cm[1, 1]),  # true positive — ANOMALY корректно
    }