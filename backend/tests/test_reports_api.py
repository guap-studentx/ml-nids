import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

from app.dependencies import get_current_user, get_report_service


class FakeReportService:
    def __init__(self, path=None):
        self.report = SimpleNamespace(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            file_path=str(path or "report.pdf"),
            format="pdf",
            created_at=datetime.now(UTC),
        )
        self.path = path

    async def create(self, *, capture_id, format="pdf"):
        self.report.session_id = capture_id
        self.report.format = format
        return self.report

    async def list(self, *, limit=50, offset=0):
        return [self.report], 1

    async def get(self, report_id):
        self.report.id = report_id
        return self.report

    def download_path(self, report):
        return self.path


def test_create_report_returns_report(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_report_service] = lambda: FakeReportService()
    capture_id = uuid.uuid4()

    response = client.post(f"/api/v1/captures/{capture_id}/report", json={"format": "pdf"})

    assert response.status_code == 201
    assert response.json()["session_id"] == str(capture_id)
    assert response.json()["status"] == "completed"


def test_list_reports_returns_items(client):
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_report_service] = lambda: FakeReportService()

    response = client.get("/api/v1/reports")

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_download_report_returns_file(client, tmp_path):
    report_path = tmp_path / "report.pdf"
    report_path.write_bytes(b"%PDF-1.4\n")
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    client.app.dependency_overrides[get_report_service] = lambda: FakeReportService(report_path)

    response = client.get(f"/api/v1/reports/{uuid.uuid4()}/download")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
