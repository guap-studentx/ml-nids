import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.database import get_session
from app.dependencies import get_capture_session_repository, get_current_user, get_live_session_service


def _live_session(status="pending"):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="continuous eth0",
        agent_id=uuid.uuid4(),
        iface="eth0",
        bpf_filter="tcp",
        model_id=uuid.uuid4(),
        status=status,
        chunk_seconds=15,
        duration_seconds=3600,
        flows_total=0,
        flows_anomaly=0,
        started_at=None,
        finished_at=None,
        created_by=uuid.uuid4(),
        error_message=None,
    )


class FakeLiveSessionService:
    def __init__(self):
        self.live_session = _live_session()

    async def create(
        self,
        *,
        name,
        agent_id,
        iface,
        bpf_filter,
        model_id,
        created_by,
        chunk_seconds,
        duration_seconds,
    ):
        self.live_session.name = name
        self.live_session.agent_id = agent_id
        self.live_session.iface = iface
        self.live_session.bpf_filter = bpf_filter
        self.live_session.model_id = model_id
        self.live_session.created_by = created_by
        self.live_session.chunk_seconds = chunk_seconds
        self.live_session.duration_seconds = duration_seconds
        return self.live_session

    async def list(self, *, status=None, agent_id=None, model_id=None, limit=50, offset=0):
        return [self.live_session], 1

    async def get(self, live_session_id):
        self.live_session.id = live_session_id
        return self.live_session

    async def stop(self, live_session_id):
        self.live_session.id = live_session_id
        self.live_session.status = "stopped"
        self.live_session.finished_at = datetime.now(UTC)
        return self.live_session

    async def delete(self, live_session_id):
        self.deleted_id = live_session_id
        return None


class FakeSession:
    async def commit(self):
        return None

    async def refresh(self, _instance):
        return None


async def fake_session():
    yield FakeSession()


class FakeCaptureRepository:
    async def list_by_live_session(self, live_session_id):
        return [
            SimpleNamespace(
                id=uuid.uuid4(),
                name="chunk 1",
                mode="live_chunk",
                source_filename="chunk.pcap",
                agent_id=uuid.uuid4(),
                iface="eth0",
                bpf_filter="tcp",
                model_id=uuid.uuid4(),
                status="completed",
                flows_total=10,
                flows_anomaly=2,
                started_at=datetime.now(UTC),
                finished_at=datetime.now(UTC),
                created_by=uuid.uuid4(),
                error_message=None,
                nfstream_settings={"chunk_seconds": 10},
                live_session_id=live_session_id,
                chunk_index=1,
            )
        ]


def test_live_sessions_require_auth(client):
    response = client.get("/api/v1/live-sessions")

    assert response.status_code == 401


def test_create_live_session_returns_pending_session(client):
    service = FakeLiveSessionService()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4(), role="admin")
    client.app.dependency_overrides[get_live_session_service] = lambda: service
    client.app.dependency_overrides[get_session] = fake_session

    response = client.post(
        "/api/v1/live-sessions",
        json={
            "name": "continuous eth0",
            "agent_id": str(uuid.uuid4()),
            "iface": "eth0",
            "model_id": str(uuid.uuid4()),
            "bpf_filter": "tcp",
            "chunk_seconds": 10,
            "duration_seconds": 600,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["chunk_seconds"] == 10
    assert body["duration_seconds"] == 600


def test_list_live_sessions_returns_items(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4(), role="admin")
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()

    response = client.get("/api/v1/live-sessions")

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["iface"] == "eth0"


def test_stop_live_session_returns_stopped_status(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4(), role="admin")
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()
    client.app.dependency_overrides[get_session] = fake_session

    response = client.post(f"/api/v1/live-sessions/{uuid.uuid4()}/stop")

    assert response.status_code == 200
    assert response.json()["status"] == "stopped"


def test_live_session_chunks_returns_capture_chunks(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4(), role="admin")
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()
    client.app.dependency_overrides[get_capture_session_repository] = lambda: FakeCaptureRepository()

    response = client.get(f"/api/v1/live-sessions/{uuid.uuid4()}/chunks")

    assert response.status_code == 200
    assert response.json()[0]["mode"] == "live_chunk"
    assert response.json()[0]["chunk_index"] == 1


def test_delete_live_session_returns_no_content(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4(), role="admin")
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()
    client.app.dependency_overrides[get_session] = fake_session

    response = client.delete(f"/api/v1/live-sessions/{uuid.uuid4()}")

    assert response.status_code == 204
