import numpy as np

from app.inference.base import BaseInferenceStrategy


class SklearnInferenceStrategy(BaseInferenceStrategy):
    def _load_model(self) -> None:
        self.model = self.artifact["model"]

    def _score(self, x: np.ndarray) -> np.ndarray:
        return self.model.predict_proba(x)[:, 1]
