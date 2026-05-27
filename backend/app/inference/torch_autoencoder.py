import numpy as np

from app.inference.base import BaseInferenceStrategy


class TorchAutoencoderStrategy(BaseInferenceStrategy):
    def _load_model(self) -> None:
        try:
            import torch
            from app.inference import architectures
        except ImportError as exc:
            raise RuntimeError("PyTorch CPU dependencies are not installed") from exc

        model_cls = getattr(architectures, self.artifact["model_class_name"])
        self.model = model_cls(**self.artifact["model_config"])
        self.model.load_state_dict(self.artifact["state_dict"])
        self.model.eval()
        self._torch = torch

    def _score(self, x: np.ndarray) -> np.ndarray:
        with self._torch.no_grad():
            tensor = self._torch.from_numpy(x)
            reconstructed = self.model(tensor)
            return ((reconstructed - tensor) ** 2).mean(dim=1).numpy()
