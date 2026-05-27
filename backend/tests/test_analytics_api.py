import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.dependencies import get_capture_analytics_service, get_current_user, get_dashboard_service
from app.schemas.analytics import (
    CaptureAnalytics,
    CaptureSummary,
    DashboardSummary,
    DashboardTimeseries,
    DashboardTimeseriesPoint,
    ScoreBucket,
)


def _capture():
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="capture",
        mode="offline_csv",
        source_filename="flows.csv",
        agent_id=None,
        iface=None,
        bpf_filter=None,
        model_id=uuid.uuid4(),
        status="completed",
        flows_total=2,
        flows_anomaly=1,
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        created_by=uuid.uuid4(),
        error_message=None,
        nfstream_settings=None,
        live_session_id=None,
        chunk_index=None,
    )


def _flow(capture_id):
    return SimpleNamespace(
        id=uuid.uuid4(),
        session_id=capture_id,
        src_ip="10.0.0.10",
        dst_ip="10.0.0.20",
        src_port=12345,
        dst_port=80,
        protocol=6,
        bidirectional_duration_ms=100,
        bidirectional_packets=3,
        bidirectional_bytes=512,
        anomaly_score=0.9,
        prediction=1,
        flow_features={"protocol": 6},
        flow_timestamp=datetime.now(UTC),
    )


class FakeCaptureAnalyticsService:
    async def build(self, capture_id):
        capture = _capture()
        capture.id = capture_id
        return CaptureAnalytics(
            capture=capture,
            summary=CaptureSummary(total_flows=2, anomaly_flows=1, anomaly_rate=50.0),
            score_distribution=[ScoreBucket(min_score=0.0, max_score=1.0, count=2)],
            anomalies_timeline=[],
            top_sources=[],
            top_destinations=[],
            recent_flows=[_flow(capture_id)],
        )


class FakeDashboardService:
    async def summary(self):
        return DashboardSummary(
            total_sessions=1,
            anomalies_24h=1,
            active_agents=0,
            active_models=8,
            recent_captures=[_capture()],
        )

    async def timeseries(self, period):
        return DashboardTimeseries(
            period_hours=24,
            points=[DashboardTimeseriesPoint(timestamp=datetime.now(UTC), anomalies=1)],
        )


def test_capture_analytics_requires_jwt(client):
    response = client.get(f"/api/v1/captures/{uuid.uuid4()}/analytics")

    assert response.status_code == 401


def test_capture_analytics_returns_sections(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_capture_analytics_service] = lambda: FakeCaptureAnalyticsService()

    response = client.get(f"/api/v1/captures/{uuid.uuid4()}/analytics")

    assert response.status_code == 200
    assert response.json()["summary"]["anomaly_rate"] == 50.0
    assert response.json()["recent_flows"][0]["prediction"] == 1


def test_dashboard_summary_returns_counts(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_dashboard_service] = lambda: FakeDashboardService()

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    assert response.json()["active_models"] == 8


def test_dashboard_timeseries_returns_points(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_dashboard_service] = lambda: FakeDashboardService()

    response = client.get("/api/v1/dashboard/timeseries?period=24h")

    assert response.status_code == 200
    assert response.json()["points"][0]["anomalies"] == 1
