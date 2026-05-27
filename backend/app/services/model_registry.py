import json
import re
from pathlib import Path

from app.exceptions import InvalidArtifactError
from app.repositories.model_repository import ModelRepository


def _slugify_model_id(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class ModelRegistryService:
    def __init__(self, models: ModelRepository):
        self.models = models

    async def load_manifest(self, artifacts_dir: Path, default_model_id: str = "xgboost") -> int:
        manifest_path = artifacts_dir / "model_registry_manifest.json"
        if not manifest_path.exists():
            raise InvalidArtifactError(f"Manifest not found: {manifest_path}")

        with manifest_path.open("r", encoding="utf-8") as file:
            manifest = json.load(file)

        features = manifest.get("model_features")
        manifest_models = manifest.get("models", [])
        if not features or not manifest_models:
            raise InvalidArtifactError("Manifest must contain model_features and models")

        loaded = 0
        for item in manifest_models:
            artifact_path = artifacts_dir / item["file"]
            if not artifact_path.exists():
                raise InvalidArtifactError(f"Artifact not found: {artifact_path}")

            model_id = _slugify_model_id(item["name"])
            await self.models.upsert_manifest_model(
                model_id=model_id,
                display_name=item["name"],
                model_class_name=item["model_class_name"],
                score_type=item["score_type"],
                decision_threshold=float(item["decision_threshold"]),
                features=features,
                metrics_test=item.get("metrics_test"),
                artifact_path=str(artifact_path),
                is_default=model_id == default_model_id,
            )
            loaded += 1

        return loaded
