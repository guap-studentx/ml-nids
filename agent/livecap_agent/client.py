from __future__ import annotations

import uuid
from pathlib import Path

import httpx


class AgentApiClient:
    def __init__(self, *, backend_url: str, agent_id: uuid.UUID, token: str, timeout: float = 10.0):
        self.backend_url = backend_url
        self.agent_id = agent_id
        self.token = token
        self.timeout = timeout

    def send_heartbeat(self, *, interfaces: list[str], metadata: dict[str, str]) -> dict:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/heartbeat"
        response = httpx.post(
            url,
            headers={"X-Agent-Token": self.token},
            json={"available_ifaces": interfaces, "metadata": metadata},
            timeout=self.timeout,
            trust_env=False,
        )
        response.raise_for_status()
        return response.json()

    def get_commands(self) -> list[dict]:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/commands"
        response = httpx.get(
            url,
            headers={"X-Agent-Token": self.token},
            timeout=self.timeout,
            trust_env=False,
        )
        response.raise_for_status()
        return response.json()["commands"]

    def upload_pcap(self, *, capture_id: str, pcap_path: Path) -> dict:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/captures/{capture_id}/pcap"
        with pcap_path.open("rb") as file_obj:
            response = httpx.post(
                url,
                headers={"X-Agent-Token": self.token},
                files={"file": (pcap_path.name, file_obj, "application/vnd.tcpdump.pcap")},
                timeout=None,
                trust_env=False,
            )
        response.raise_for_status()
        return response.json()

    def upload_live_session_chunk(self, *, live_session_id: str, pcap_path: Path) -> dict:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/live-sessions/{live_session_id}/chunks"
        with pcap_path.open("rb") as file_obj:
            response = httpx.post(
                url,
                headers={"X-Agent-Token": self.token},
                files={"file": (pcap_path.name, file_obj, "application/vnd.tcpdump.pcap")},
                timeout=None,
                trust_env=False,
            )
        response.raise_for_status()
        return response.json()

    def fail_capture(self, *, capture_id: str, error_message: str) -> None:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/captures/{capture_id}/fail"
        response = httpx.post(
            url,
            headers={"X-Agent-Token": self.token},
            json={"error_message": error_message},
            timeout=self.timeout,
            trust_env=False,
        )
        response.raise_for_status()

    def fail_live_session(self, *, live_session_id: str, error_message: str) -> None:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/live-sessions/{live_session_id}/fail"
        response = httpx.post(
            url,
            headers={"X-Agent-Token": self.token},
            json={"error_message": error_message},
            timeout=self.timeout,
            trust_env=False,
        )
        response.raise_for_status()

    def capture_status(self, *, capture_id: str, timeout: float | None = None) -> str:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/captures/{capture_id}/status"
        response = httpx.get(
            url,
            headers={"X-Agent-Token": self.token},
            timeout=self.timeout if timeout is None else timeout,
            trust_env=False,
        )
        response.raise_for_status()
        return response.json()["status"]

    def live_session_status(self, *, live_session_id: str, timeout: float | None = None) -> str:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/live-sessions/{live_session_id}/status"
        response = httpx.get(
            url,
            headers={"X-Agent-Token": self.token},
            timeout=self.timeout if timeout is None else timeout,
            trust_env=False,
        )
        response.raise_for_status()
        return response.json()["status"]

    def complete_live_session(self, *, live_session_id: str) -> None:
        url = f"{self.backend_url}/api/v1/agents/{self.agent_id}/live-sessions/{live_session_id}/complete"
        response = httpx.post(
            url,
            headers={"X-Agent-Token": self.token},
            timeout=self.timeout,
            trust_env=False,
        )
        response.raise_for_status()
