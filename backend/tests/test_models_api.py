import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.dependencies import get_current_user, get_model_service, require_admin
from app.exceptions import ModelNotFoundError


def _model(**overrides):
    values = {
        "id": uuid.uuid4(),
        "model_id": "xgboost",
        "display_name": "XGBoost",
        "model_class_name": "XGBClassifier",
        "score_type": "predict_proba",
        "decision_threshold": 0.5,
        "features": ["protocol"],
        "metrics_test": {"f1_anomaly": 0.99},
        "artifact_path": "/models/model_xgboost.joblib",
        "is_active": True,
        "is_default": True,
        "uploaded_at": datetime.now(UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class FakeModelService:
    def __init__(self):
        self.item = _model()

    async def list(self):
        return [self.item]

    async def get(self, model_id):
        if model_id == self.item.id:
            return self.item
        raise ModelNotFoundError()

    async def detail(self, model_id):
        return await self.get(model_id), {
            "metrics_train": {"f1_anomaly": 1.0},
            "architecture_config": {"max_depth": 3},
            "n_params": None,
            "fit_time_sec": 1.2,
            "predict_time_test_sec": 0.1,
            "size_kb": 10.0,
            "feature_importance": [{"feature": "protocol", "importance": 0.42}],
        }

    async def create_from_artifact(self, *, artifact_path, uploaded_by, model_id=None, display_name=None):
        self.item = _model(
            id=uuid.uuid4(),
            model_id=model_id or "uploaded_model",
            display_name=display_name or "Uploaded model",
            artifact_path=str(artifact_path),
            is_default=False,
        )
        return self.item

    async def update(self, model_id, *, is_active=None, is_default=None):
        model = await self.get(model_id)
        if is_active is not None:
            model.is_active = is_active
        if is_default is not None:
            model.is_default = is_default
        return model

    async def delete(self, model_id):
        await self.get(model_id)


def test_models_require_jwt(client):
    response = client.get("/api/v1/models")

    assert response.status_code == 401


def test_models_list_returns_items_for_current_user(client):
    service = FakeModelService()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_model_service] = lambda: service

    response = client.get("/api/v1/models")

    assert response.status_code == 200
    assert response.json()[0]["model_id"] == "xgboost"


def test_model_detail_returns_404_for_unknown_model(client):
    service = FakeModelService()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_model_service] = lambda: service

    response = client.get(f"/api/v1/models/{uuid.uuid4()}")

    assert response.status_code == 404


def test_model_detail_returns_extra_artifact_fields(client):
    service = FakeModelService()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_model_service] = lambda: service

    response = client.get(f"/api/v1/models/{service.item.id}")

    assert response.status_code == 200
    assert response.json()["architecture_config"]["max_depth"] == 3
    assert response.json()["feature_importance"][0]["feature"] == "protocol"


def test_patch_model_requires_admin(client):
    response = client.patch(f"/api/v1/models/{uuid.uuid4()}", json={"is_active": False})

    assert response.status_code == 401


def test_patch_model_updates_flags(client):
    service = FakeModelService()
    client.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_model_service] = lambda: service

    response = client.patch(f"/api/v1/models/{service.item.id}", json={"is_active": False, "is_default": False})

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["is_default"] is False


def test_delete_model_returns_no_content(client):
    service = FakeModelService()
    service.item.is_default = False
    client.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_model_service] = lambda: service

    response = client.delete(f"/api/v1/models/{service.item.id}")

    assert response.status_code == 204
