import json

import pytest

pd = pytest.importorskip("pandas")

from app.inference.validation import FeatureFrameValidator, FeatureValidationError  # noqa: E402


def _write_config(tmp_path, features):
    path = tmp_path / "preprocessing_config.json"
    path.write_text(json.dumps({"model_features": features}), encoding="utf-8")
    return path


def test_feature_validator_returns_numeric_frame(tmp_path):
    validator = FeatureFrameValidator(_write_config(tmp_path, ["protocol", "src2dst_packets"]))
    df = pd.DataFrame({"protocol": ["6"], "src2dst_packets": ["10"], "src_ip": ["10.0.0.1"]})

    result = validator.validate(df)

    assert result["protocol"].iloc[0] == 6
    assert result["src2dst_packets"].iloc[0] == 10
    assert result["src_ip"].iloc[0] == "10.0.0.1"


def test_feature_validator_reports_missing_features(tmp_path):
    validator = FeatureFrameValidator(_write_config(tmp_path, ["protocol", "src2dst_packets"]))

    with pytest.raises(FeatureValidationError, match="src2dst_packets"):
        validator.validate(pd.DataFrame({"protocol": [6]}))


def test_feature_validator_reports_non_numeric_features(tmp_path):
    validator = FeatureFrameValidator(_write_config(tmp_path, ["protocol"]))

    with pytest.raises(FeatureValidationError, match="protocol"):
        validator.validate(pd.DataFrame({"protocol": ["tcp"]}))
