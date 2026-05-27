from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from sqlalchemy.exc import IntegrityError

from app.exceptions import InvalidArtifactError, ModelConflictError, ModelNotFoundError
from app.models.ml_model import MLModel
from app.repositories.model_repository import ModelRepository
from app.services.model_registry import _slugify_model_id


class ModelService:
    def __init__(self, models: ModelRepository):
        self.models = models

    async def list(self) -> list[MLModel]:
        return await self.models.list()

    async def get(self, model_id: uuid.UUID) -> MLModel:
        model = await self.models.get(model_id)
        if model is None:
            raise ModelNotFoundError()
        return model

    async def detail(self, model_id: uuid.UUID) -> tuple[MLModel, dict[str, Any]]:
        model = await self.get(model_id)
        artifact = self._load_artifact(Path(model.artifact_path))
        return model, self._artifact_details(artifact, model.features)

    async def create_from_artifact(
        self,
        *,
        artifact_path: Path,
        uploaded_by: uuid.UUID | None,
        model_id: str | None = None,
        display_name: str | None = None,
    ) -> MLModel:
        artifact = self._load_artifact(artifact_path)
        features = artifact.get("model_features")
        if not isinstance(features, list) or not features:
            raise InvalidArtifactError("Artifact must contain non-empty model_features")

        class_name = self._required_str(artifact, "model_class_name")
        score_type = self._required_str(artifact, "score_type")
        if score_type not in {"predict_proba", "reconstruction_error"}:
            raise InvalidArtifactError("Unsupported score_type")
        if "decision_threshold" not in artifact:
            raise InvalidArtifactError("Artifact must contain decision_threshold")

        resolved_display_name = display_name or artifact.get("name") or class_name
        resolved_model_id = model_id or _slugify_model_id(resolved_display_name)
        if not resolved_model_id:
            raise InvalidArtifactError("model_id cannot be empty")
        if await self.models.get_by_model_id(resolved_model_id):
            raise ModelConflictError("Model id already exists")

        return await self.models.create_uploaded_model(
            model_id=resolved_model_id,
            display_name=resolved_display_name,
            model_class_name=class_name,
            score_type=score_type,
            decision_threshold=float(artifact["decision_threshold"]),
            features=[str(feature) for feature in features],
            metrics_test=artifact.get("metrics_test"),
            artifact_path=str(artifact_path),
            uploaded_by=uploaded_by,
        )

    async def update(
        self,
        model_id: uuid.UUID,
        *,
        is_active: bool | None = None,
        is_default: bool | None = None,
    ) -> MLModel:
        model = await self.get(model_id)
        if is_active is not None:
            model.is_active = is_active
        if is_default is not None:
            if is_default:
                await self.models.unset_default()
                model.is_active = True
            model.is_default = is_default
        return model

    async def delete(self, model_id: uuid.UUID) -> None:
        model = await self.get(model_id)
        if model.is_default:
            raise ModelConflictError("Default model cannot be deleted")
        try:
            await self.models.delete(model)
        except IntegrityError as exc:
            raise ModelConflictError("Model is used by capture sessions") from exc

    def _load_artifact(self, artifact_path: Path) -> dict[str, Any]:
        if not artifact_path.exists():
            raise InvalidArtifactError(f"Artifact not found: {artifact_path}")
        import joblib
        from app.inference.compat import install_joblib_compat_shims

        install_joblib_compat_shims()
        artifact = joblib.load(artifact_path)
        if not isinstance(artifact, dict):
            raise InvalidArtifactError("Artifact must be a dictionary")
        return artifact

    def _required_str(self, artifact: dict[str, Any], key: str) -> str:
        value = artifact.get(key)
        if not isinstance(value, str) or not value:
            raise InvalidArtifactError(f"Artifact must contain {key}")
        return value

    def _artifact_details(self, artifact: dict[str, Any], features: list[str]) -> dict[str, Any]:
        return {
            "metrics_train": artifact.get("metrics_train"),
            "architecture_config": artifact.get("model_config"),
            "n_params": artifact.get("n_params"),
            "fit_time_sec": artifact.get("fit_time_sec"),
            "predict_time_test_sec": artifact.get("predict_time_test_sec"),
            "size_kb": artifact.get("size_kb"),
            "feature_importance": self._feature_importance(artifact, features),
        }

    def _feature_importance(self, artifact: dict[str, Any], features: list[str]) -> list[dict[str, float | str]]:
        raw_importance = artifact.get("feature_importance") or artifact.get("feature_importances")
        if isinstance(raw_importance, dict):
            return self._sorted_importance(raw_importance)
        if isinstance(raw_importance, list) and raw_importance and isinstance(raw_importance[0], dict):
            values = {
                str(item.get("feature")): float(item.get("importance", 0))
                for item in raw_importance
                if item.get("feature")
            }
            return self._sorted_importance(values)

        model = artifact.get("model")
        values = None
        if model is not None and hasattr(model, "feature_importances_"):
            values = getattr(model, "feature_importances_")
        elif model is not None and hasattr(model, "coef_"):
            coef = getattr(model, "coef_")
            try:
                values = abs(coef[0] if getattr(coef, "ndim", 1) > 1 else coef)
            except TypeError:
                values = None
        if values is None:
            return []

        return self._sorted_importance(
            {feature: float(value) for feature, value in zip(features, values, strict=False)}
        )

    def _sorted_importance(self, values: dict[str, float]) -> list[dict[str, float | str]]:
        return [
            {"feature": feature, "importance": importance}
            for feature, importance in sorted(values.items(), key=lambda item: abs(item[1]), reverse=True)
            if importance is not None
        ][:30]
