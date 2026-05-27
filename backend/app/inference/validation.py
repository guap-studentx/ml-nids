from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


class FeatureValidationError(ValueError):
    pass


class FeatureFrameValidator:
    def __init__(self, preprocessing_config_path: Path):
        self.preprocessing_config_path = preprocessing_config_path
        self._required_features: list[str] | None = None

    @property
    def required_features(self) -> list[str]:
        if self._required_features is None:
            config = json.loads(self.preprocessing_config_path.read_text(encoding="utf-8"))
            self._required_features = list(config["model_features"])
        return self._required_features

    def validate(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            raise FeatureValidationError("No flows available for inference after preprocessing")

        missing = [feature for feature in self.required_features if feature not in df.columns]
        if missing:
            preview = ", ".join(missing[:10])
            suffix = "" if len(missing) <= 10 else f" (+{len(missing) - 10} more)"
            raise FeatureValidationError(f"Input flow data is missing required model features: {preview}{suffix}")

        result = df.copy()
        invalid_features: list[str] = []
        for feature in self.required_features:
            numeric = pd.to_numeric(result[feature], errors="coerce")
            if numeric.isna().all() and len(numeric) > 0:
                invalid_features.append(feature)
            result[feature] = numeric

        if invalid_features:
            preview = ", ".join(invalid_features[:10])
            suffix = "" if len(invalid_features) <= 10 else f" (+{len(invalid_features) - 10} more)"
            raise FeatureValidationError(f"Input flow data has non-numeric required features: {preview}{suffix}")

        return result
