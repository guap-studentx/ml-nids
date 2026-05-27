from __future__ import annotations

import argparse
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentConfig:
    backend_url: str
    agent_id: uuid.UUID
    token: str
    interval_seconds: float
    work_dir: Path
    keep_pcaps: bool
    max_pcap_files: int
    pcap_retention_hours: float
    once: bool


def parse_config(argv: list[str] | None = None) -> AgentConfig:
    parser = argparse.ArgumentParser(description="ML-NIDS host-side live capture agent")
    parser.add_argument("--config", default=os.getenv("ML_NIDS_AGENT_CONFIG"), help="path to JSON config file")
    parser.add_argument("--write-config", action="store_true", help="write resolved settings to --config and exit")
    parser.add_argument("--backend-url", default=None)
    parser.add_argument("--agent-id", default=None)
    parser.add_argument("--token", default=None)
    parser.add_argument("--interval", type=float, default=None)
    parser.add_argument("--work-dir", default=None)
    parser.add_argument("--keep-pcaps", action="store_true", default=None, help="keep uploaded PCAP files in work-dir")
    parser.add_argument("--max-pcap-files", type=int, default=None)
    parser.add_argument("--pcap-retention-hours", type=float, default=None)
    parser.add_argument("--once", action="store_true", help="send one heartbeat and exit")
    args = parser.parse_args(argv)

    file_config = _read_config(Path(args.config)) if args.config else {}
    backend_url = _coalesce(args.backend_url, file_config.get("backend_url"), os.getenv("ML_NIDS_BACKEND_URL"), "http://localhost:8000")
    agent_id_value = _coalesce(args.agent_id, file_config.get("agent_id"), os.getenv("ML_NIDS_AGENT_ID"))
    token = _coalesce(args.token, file_config.get("token"), os.getenv("ML_NIDS_AGENT_TOKEN"))
    interval = float(_coalesce(args.interval, file_config.get("interval_seconds"), os.getenv("ML_NIDS_AGENT_INTERVAL"), 10))
    work_dir = _coalesce(args.work_dir, file_config.get("work_dir"), os.getenv("ML_NIDS_AGENT_WORK_DIR"), ".livecap-agent")
    keep_pcaps = _optional_bool(_coalesce(args.keep_pcaps, file_config.get("keep_pcaps"), os.getenv("ML_NIDS_AGENT_KEEP_PCAPS"), False))
    max_pcap_files = int(_coalesce(args.max_pcap_files, file_config.get("max_pcap_files"), os.getenv("ML_NIDS_AGENT_MAX_PCAP_FILES"), 100))
    pcap_retention_hours = float(
        _coalesce(
            args.pcap_retention_hours,
            file_config.get("pcap_retention_hours"),
            os.getenv("ML_NIDS_AGENT_PCAP_RETENTION_HOURS"),
            24,
        )
    )

    if not agent_id_value:
        parser.error("--agent-id, config agent_id, or ML_NIDS_AGENT_ID is required")
    if not token:
        parser.error("--token, config token, or ML_NIDS_AGENT_TOKEN is required")
    if interval <= 0:
        parser.error("--interval must be greater than 0")
    if max_pcap_files < 0:
        parser.error("--max-pcap-files must be greater than or equal to 0")
    if pcap_retention_hours <= 0:
        parser.error("--pcap-retention-hours must be greater than 0")

    try:
        agent_id = uuid.UUID(agent_id_value)
    except ValueError as exc:
        parser.error("--agent-id must be a valid UUID")
        raise exc

    config = AgentConfig(
        backend_url=backend_url.rstrip("/"),
        agent_id=agent_id,
        token=token,
        interval_seconds=interval,
        work_dir=Path(work_dir),
        keep_pcaps=keep_pcaps,
        max_pcap_files=max_pcap_files,
        pcap_retention_hours=pcap_retention_hours,
        once=args.once,
    )
    if args.write_config:
        if not args.config:
            parser.error("--write-config requires --config")
        _write_config(Path(args.config), config)
        raise SystemExit(0)
    return config


def _coalesce(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _read_config(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON config {path}: {exc}") from exc


def _optional_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _write_config(path: Path, config: AgentConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "backend_url": config.backend_url,
        "agent_id": str(config.agent_id),
        "token": config.token,
        "interval_seconds": config.interval_seconds,
        "work_dir": str(config.work_dir),
        "keep_pcaps": config.keep_pcaps,
        "max_pcap_files": config.max_pcap_files,
        "pcap_retention_hours": config.pcap_retention_hours,
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Config written: {path}")
