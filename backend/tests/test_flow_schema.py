import uuid
from datetime import UTC, datetime
from ipaddress import IPv4Address
from types import SimpleNamespace

import pytest

from app.schemas.flow import FlowRead


def test_flow_read_serializes_postgres_inet_values():
    flow = SimpleNamespace(
        id=uuid.uuid4(),
        session_id=uuid.uuid4(),
        src_ip=IPv4Address("192.168.131.2"),
        dst_ip=IPv4Address("192.168.128.40"),
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

    dto = FlowRead.model_validate(flow)

    assert dto.src_ip == "192.168.131.2"
    assert dto.dst_ip == "192.168.128.40"


def test_flow_storage_does_not_use_expiration_id_as_timestamp():
    pd = pytest.importorskip("pandas")
    from app.services.flow_storage_service import FlowStorageService

    row = pd.Series({"expiration_id": 0, "bidirectional_first_seen_ms": 1_700_000_000_000})
    service = FlowStorageService(flows=None, captures_dir=None)

    timestamp = service._optional_timestamp(row)

    assert timestamp.year == 2023
