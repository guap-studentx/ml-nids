import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from app.dependencies import get_agent_service, get_capture_service, get_live_session_service, require_admin
from app.exceptions import AgentOfflineError
from app.services.agent_service import AgentService


def _agent(status="offline", ifaces=None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="sensor-1",
        last_seen_at=datetime.now(UTC),
        status=status,
        available_ifaces=ifaces,
        agent_metadata=None,
    )


class FakeAgentService:
    def __init__(self):
        self.agent = _agent(status="online", ifaces=["eth0"])

    async def list(self):
        return [self.agent]

    async def create(self, *, name):
        agent = _agent()
        agent.name = name
        return agent, "plain-token"

    async def delete(self, agent_id):
        return None

    async def ifaces(self, agent_id):
        return ["eth0"]

    async def heartbeat(self, agent_id, *, token, available_ifaces, metadata=None):
        if token != "plain-token":
            from app.exceptions import AuthError

            raise AuthError()
        self.agent.id = agent_id
        self.agent.available_ifaces = available_ifaces
        self.agent.agent_metadata = metadata
        self.agent.status = "online"
        return self.agent

    async def authenticate(self, agent_id, *, token):
        if token != "plain-token":
            from app.exceptions import AuthError

            raise AuthError()
        self.agent.id = agent_id
        return self.agent


class OfflineAgentService(FakeAgentService):
    async def ifaces(self, agent_id):
        raise AgentOfflineError()


class FakeCaptureService:
    def __init__(self):
        self.capture = SimpleNamespace(
            id=uuid.uuid4(),
            iface="Ethernet",
            bpf_filter="tcp",
            status="running",
            nfstream_settings={"duration_seconds": 3},
        )

    async def claim_next_live_command(self, agent_id):
        return self.capture

    async def ensure_agent_capture(self, *, agent_id, capture_id):
        return self.capture

    async def fail_agent_capture(self, *, agent_id, capture_id, error_message):
        self.capture.error_message = error_message
        return self.capture

    async def agent_capture_status(self, *, agent_id, capture_id):
        return self.capture.status


class EmptyCaptureService(FakeCaptureService):
    async def claim_next_live_command(self, agent_id):
        return None


class FakeLiveSessionService:
    def __init__(self):
        self.live_session = SimpleNamespace(
            id=uuid.uuid4(),
            iface="eth0",
            bpf_filter="tcp",
            status="running",
            duration_seconds=600,
            chunk_seconds=10,
            model_id=uuid.uuid4(),
            agent_id=uuid.uuid4(),
        )

    async def claim_next_command(self, agent_id):
        return self.live_session

    async def fail_agent_live_session(self, *, agent_id, live_session_id, error_message):
        self.live_session.status = "failed"
        self.live_session.error_message = error_message
        return self.live_session

    async def agent_live_session_status(self, *, agent_id, live_session_id):
        return self.live_session.status

    async def complete_agent_live_session(self, *, agent_id, live_session_id):
        self.live_session.status = "completed"
        return self.live_session


class EmptyLiveSessionService(FakeLiveSessionService):
    async def claim_next_command(self, agent_id):
        return None


def test_agents_require_admin(client):
    response = client.get("/api/v1/agents")

    assert response.status_code == 401


def test_list_agents_returns_items(client):
    client.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.get("/api/v1/agents")

    assert response.status_code == 200
    assert response.json()[0]["name"] == "sensor-1"


def test_create_agent_returns_one_time_token(client):
    client.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.post("/api/v1/agents", json={"name": "sensor-new"})

    assert response.status_code == 201
    assert response.json()["name"] == "sensor-new"
    assert response.json()["agent_token"] == "plain-token"


def test_agent_ifaces_returns_online_ifaces(client):
    client.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.get(f"/api/v1/agents/{uuid.uuid4()}/ifaces")

    assert response.status_code == 200
    assert response.json()["ifaces"] == ["eth0"]


def test_agent_ifaces_rejects_offline_agent(client):
    client.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_agent_service] = lambda: OfflineAgentService()

    response = client.get(f"/api/v1/agents/{uuid.uuid4()}/ifaces")

    assert response.status_code == 409


def test_delete_agent_returns_no_content(client):
    client.app.dependency_overrides[require_admin] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.delete(f"/api/v1/agents/{uuid.uuid4()}")

    assert response.status_code == 204


def test_agent_heartbeat_marks_agent_online(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    agent_id = uuid.uuid4()

    response = client.post(
        f"/api/v1/agents/{agent_id}/heartbeat",
        headers={"X-Agent-Token": "plain-token"},
        json={"available_ifaces": ["Ethernet"], "metadata": {"hostname": "sensor-host"}},
    )

    assert response.status_code == 200
    assert response.json()["agent_id"] == str(agent_id)
    assert response.json()["status"] == "online"


def test_agent_heartbeat_requires_token(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.post(f"/api/v1/agents/{uuid.uuid4()}/heartbeat", json={"available_ifaces": []})

    assert response.status_code == 401


def test_agent_heartbeat_rejects_invalid_token(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()

    response = client.post(
        f"/api/v1/agents/{uuid.uuid4()}/heartbeat",
        headers={"X-Agent-Token": "bad-token"},
        json={"available_ifaces": []},
    )

    assert response.status_code == 401


def test_agent_commands_claims_next_live_capture(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client.app.dependency_overrides[get_capture_service] = lambda: FakeCaptureService()
    client.app.dependency_overrides[get_live_session_service] = lambda: EmptyLiveSessionService()

    response = client.get(f"/api/v1/agents/{uuid.uuid4()}/commands", headers={"X-Agent-Token": "plain-token"})

    assert response.status_code == 200
    command = response.json()["commands"][0]
    assert command["type"] == "capture"
    assert command["iface"] == "Ethernet"
    assert command["bpf_filter"] == "tcp"
    assert command["duration_seconds"] == 3


def test_agent_commands_claims_next_live_session_when_no_capture(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client.app.dependency_overrides[get_capture_service] = lambda: EmptyCaptureService()
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()

    response = client.get(f"/api/v1/agents/{uuid.uuid4()}/commands", headers={"X-Agent-Token": "plain-token"})

    assert response.status_code == 200
    command = response.json()["commands"][0]
    assert command["type"] == "live_session"
    assert command["iface"] == "eth0"
    assert command["chunk_seconds"] == 10
    assert command["duration_seconds"] == 600
    assert command["live_session_id"] is not None


def test_agent_capture_fail_marks_capture_failed(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client.app.dependency_overrides[get_capture_service] = lambda: FakeCaptureService()

    response = client.post(
        f"/api/v1/agents/{uuid.uuid4()}/captures/{uuid.uuid4()}/fail",
        headers={"X-Agent-Token": "plain-token"},
        json={"error_message": "dumpcap failed"},
    )

    assert response.status_code == 204


def test_agent_capture_status_returns_status(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client.app.dependency_overrides[get_capture_service] = lambda: FakeCaptureService()

    response = client.get(
        f"/api/v1/agents/{uuid.uuid4()}/captures/{uuid.uuid4()}/status",
        headers={"X-Agent-Token": "plain-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_agent_live_session_fail_marks_session_failed(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()

    response = client.post(
        f"/api/v1/agents/{uuid.uuid4()}/live-sessions/{uuid.uuid4()}/fail",
        headers={"X-Agent-Token": "plain-token"},
        json={"error_message": "continuous mode unsupported"},
    )

    assert response.status_code == 204


def test_agent_live_session_status_returns_status(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()

    response = client.get(
        f"/api/v1/agents/{uuid.uuid4()}/live-sessions/{uuid.uuid4()}/status",
        headers={"X-Agent-Token": "plain-token"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "running"
    assert response.json()["live_session_id"] is not None


def test_agent_live_session_complete_returns_no_content(client):
    client.app.dependency_overrides[get_agent_service] = lambda: FakeAgentService()
    client.app.dependency_overrides[get_live_session_service] = lambda: FakeLiveSessionService()

    response = client.post(
        f"/api/v1/agents/{uuid.uuid4()}/live-sessions/{uuid.uuid4()}/complete",
        headers={"X-Agent-Token": "plain-token"},
    )

    assert response.status_code == 204


def test_effective_status_marks_stale_online_agent_offline():
    service = AgentService(agents=SimpleNamespace(), offline_after_seconds=30)
    agent = _agent(status="online")
    agent.last_seen_at = datetime.now(UTC) - timedelta(seconds=31)

    assert service.effective_status(agent) == "offline"


def test_effective_status_keeps_recent_online_agent_online():
    service = AgentService(agents=SimpleNamespace(), offline_after_seconds=30)
    agent = _agent(status="online")
    agent.last_seen_at = datetime.now(UTC) - timedelta(seconds=5)

    assert service.effective_status(agent) == "online"
