from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


class BaseInferenceStrategy(ABC):
    def __init__(self, artifact: dict, preprocessor, feature_names: list[str]):
        self.artifact = artifact
        self.features = artifact["model_features"]
        self.threshold = artifact["decision_threshold"]
        self.score_type = artifact["score_type"]
        self.preprocessor = preprocessor
        self.feature_names = feature_names
        self._load_model()

    @abstractmethod
    def _load_model(self) -> None:
        pass

    @abstractmethod
    def _score(self, x: np.ndarray) -> np.ndarray:
        pass

    def predict(self, df_raw: pd.DataFrame) -> pd.DataFrame:
        missing = [column for column in self.features if column not in df_raw.columns]
        if missing:
            raise ValueError(f"Missing columns: {missing}")

        transformed = self.preprocessor.transform(df_raw)
        if isinstance(transformed, pd.DataFrame):
            x_preprocessed = transformed[self.feature_names]
        else:
            x_preprocessed = pd.DataFrame(transformed, columns=self.feature_names, index=df_raw.index)
        score = self._score(x_preprocessed.values.astype(np.float32))
        prediction = (score >= self.threshold).astype(int)

        result = df_raw.copy()
        result["anomaly_score"] = score
        result["prediction"] = prediction
        result["prediction_label"] = np.where(prediction == 1, "ANOMALY", "BENIGN")
        return result
