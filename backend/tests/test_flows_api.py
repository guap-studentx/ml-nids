import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.dependencies import get_current_user, get_flow_service


def _flow(score: float = 0.9):
    return SimpleNamespace(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        src_ip="10.0.0.10",
        dst_ip="10.0.0.20",
        src_port=12345,
        dst_port=80,
        protocol=6,
        bidirectional_duration_ms=100,
        bidirectional_packets=3,
        bidirectional_bytes=512,
        anomaly_score=score,
        prediction=1,
        flow_features={"protocol": 6},
        flow_timestamp=datetime.now(UTC),
    )


class FakeFlowService:
    def __init__(self, export_file=None):
        self.item = _flow()
        self.export_file = export_file

    async def list(self, **kwargs):
        return [self.item], 1

    async def top(self, **kwargs):
        return [self.item]

    async def get(self, **kwargs):
        return self.item

    def explain(self, flow):
        return [{"feature": "anomaly_score", "value": flow.anomaly_score, "contribution": flow.anomaly_score}]

    async def export_path(self, **kwargs):
        return self.export_file


def test_flows_require_jwt(client):
    response = client.get(f"/api/v1/captures/{uuid.uuid4()}/flows")

    assert response.status_code == 401


def test_flows_list_returns_items(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_flow_service] = lambda: FakeFlowService()

    response = client.get(f"/api/v1/captures/{uuid.uuid4()}/flows")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["prediction"] == 1


def test_top_flows_returns_items(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_flow_service] = lambda: FakeFlowService()

    response = client.get(f"/api/v1/captures/{uuid.uuid4()}/flows/top?n=5")

    assert response.status_code == 200
    assert response.json()[0]["anomaly_score"] == 0.9


def test_flow_detail_returns_explanation(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_flow_service] = lambda: FakeFlowService()

    response = client.get(f"/api/v1/captures/{uuid.uuid4()}/flows/{uuid.uuid4()}")

    assert response.status_code == 200
    assert response.json()["flow"]["prediction"] == 1
    assert response.json()["explanation"][0]["feature"] == "anomaly_score"


def test_export_flows_downloads_file(client, tmp_path):
    export_path = tmp_path / "flows.csv"
    export_path.write_text("protocol,prediction\n6,1\n", encoding="utf-8")
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_flow_service] = lambda: FakeFlowService(export_path)

    response = client.get(f"/api/v1/captures/{uuid.uuid4()}/flows/export?format=csv")

    assert response.status_code == 200
    assert "protocol,prediction" in response.text
