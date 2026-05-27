from __future__ import annotations

import re
import socket
import subprocess

from livecap_agent.tools import find_executable


def list_interfaces() -> list[str]:
    for tool in ("dumpcap", "tshark"):
        names = _list_capture_tool_interfaces(tool)
        if names:
            return names

    try:
        names = [name for _, name in socket.if_nameindex()]
    except OSError:
        return []
    return sorted({name for name in names if name})


def _list_capture_tool_interfaces(tool: str) -> list[str]:
    executable = find_executable(tool)
    if executable is None:
        return []
    try:
        result = subprocess.run([executable, "-D"], check=False, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return []
    if result.returncode != 0:
        return []

    interfaces = []
    for line in result.stdout.splitlines():
        match = re.match(r"\s*\d+\.\s+(.+?)\s*$", line)
        if match:
            interfaces.append(match.group(1))
    return interfaces
