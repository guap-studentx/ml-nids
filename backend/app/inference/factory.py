from app.inference.base import BaseInferenceStrategy
from app.inference.sklearn_strategy import SklearnInferenceStrategy
from app.inference.torch_autoencoder import TorchAutoencoderStrategy
from app.inference.torch_supervised import TorchSupervisedStrategy


class InferenceStrategyFactory:
    @staticmethod
    def create(artifact: dict, preprocessor, feature_names: list[str]) -> BaseInferenceStrategy:
        score_type = artifact["score_type"]
        class_name = artifact["model_class_name"]

        if score_type == "reconstruction_error":
            return TorchAutoencoderStrategy(artifact, preprocessor, feature_names)

        if class_name in ("TabularMLP", "TabularFTTransformer"):
            return TorchSupervisedStrategy(artifact, preprocessor, feature_names)

        return SklearnInferenceStrategy(artifact, preprocessor, feature_names)
