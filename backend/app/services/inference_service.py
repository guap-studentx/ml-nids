import asyncio
import json
from pathlib import Path

import joblib
import pandas as pd

from app.inference.compat import install_joblib_compat_shims
from app.inference.factory import InferenceStrategyFactory
from app.inference.validation import FeatureFrameValidator
from app.models.ml_model import MLModel


class InferenceService:
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self._preprocessor = None
        self._feature_names: list[str] | None = None
        self._strategies = {}
        self._validator = FeatureFrameValidator(models_dir / "preprocessing_config.json")

    async def predict(self, model: MLModel, df_raw: pd.DataFrame) -> pd.DataFrame:
        strategy = await self._get_strategy(model)
        df_validated = await asyncio.to_thread(self._validator.validate, df_raw)
        return await asyncio.to_thread(strategy.predict, df_validated)

    async def _get_strategy(self, model: MLModel):
        install_joblib_compat_shims()
        cached = self._strategies.get(model.model_id)
        if cached is not None:
            return cached

        preprocessor = await self._get_preprocessor()
        feature_names = await self._get_feature_names()
        artifact = await asyncio.to_thread(joblib.load, model.artifact_path)
        strategy = await asyncio.to_thread(InferenceStrategyFactory.create, artifact, preprocessor, feature_names)
        self._strategies[model.model_id] = strategy
        return strategy

    async def _get_preprocessor(self):
        if self._preprocessor is None:
            install_joblib_compat_shims()
            self._preprocessor = await asyncio.to_thread(joblib.load, self.models_dir / "preprocessor.joblib")
        return self._preprocessor

    async def _get_feature_names(self) -> list[str]:
        if self._feature_names is None:
            feature_names_path = self.models_dir / "feature_names.json"
            content = await asyncio.to_thread(feature_names_path.read_text, encoding="utf-8")
            self._feature_names = json.loads(content)["feature_names"]
        return self._feature_names
