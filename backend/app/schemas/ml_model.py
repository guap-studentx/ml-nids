import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class MLModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_id: str
    display_name: str
    model_class_name: str
    score_type: str
    decision_threshold: float
    features: list[str]
    metrics_test: dict[str, Any] | None
    artifact_path: str
    is_active: bool
    is_default: bool
    uploaded_at: datetime


class MLModelUpdate(BaseModel):
    is_active: bool | None = None
    is_default: bool | None = None


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float


class MLModelDetail(MLModelRead):
    metrics_train: dict[str, Any] | None = None
    architecture_config: dict[str, Any] | None = None
    n_params: int | None = None
    fit_time_sec: float | None = None
    predict_time_test_sec: float | None = None
    size_kb: float | None = None
    feature_importance: list[FeatureImportanceItem] = Field(default_factory=list)
