from __future__ import annotations

import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from livecap_agent.tools import find_executable


class CaptureToolError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaptureCommand:
    args: list[str]
    stdout_path: Path | None = None
    max_duration_seconds: int | None = None


def capture_pcap(
    *,
    iface: str,
    duration_seconds: int,
    output_path: Path,
    bpf_filter: str | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    command = _build_command(
        iface=_capture_identifier(iface),
        duration_seconds=duration_seconds,
        output_path=output_path,
        bpf_filter=bpf_filter,
    )
    try:
        result = _run_capture(command, should_stop=should_stop)
    except OSError as exc:
        raise CaptureToolError(str(exc)) from exc

    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "capture tool failed").strip()
        raise CaptureToolError(detail)
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise CaptureToolError("capture tool produced an empty PCAP file")


def _run_capture(command: CaptureCommand, *, should_stop: Callable[[], bool] | None) -> subprocess.CompletedProcess:
    stdout_file = command.stdout_path.open("wb") if command.stdout_path else None
    process = subprocess.Popen(
        command.args,
        stdout=stdout_file or subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=stdout_file is None,
    )
    stopped = False
    try:
        started_at = time.monotonic()
        while process.poll() is None:
            if should_stop and should_stop():
                stopped = True
                process.terminate()
                break
            if command.max_duration_seconds and time.monotonic() - started_at >= command.max_duration_seconds:
                stopped = True
                process.terminate()
                break
            time.sleep(1)

        try:
            stdout, stderr = process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
    finally:
        if stdout_file:
            stdout_file.close()

    if isinstance(stderr, bytes):
        stderr = stderr.decode(errors="replace")
    if isinstance(stdout, bytes):
        stdout = stdout.decode(errors="replace")

    return subprocess.CompletedProcess(command.args, 0 if stopped else process.returncode, stdout or "", stderr or "")


def _build_command(*, iface: str, duration_seconds: int, output_path: Path, bpf_filter: str | None) -> CaptureCommand:
    if dumpcap := find_executable("dumpcap"):
        command = [dumpcap, "-i", iface, "-a", f"duration:{duration_seconds}", "-w", str(output_path)]
        if bpf_filter:
            command.extend(["-f", bpf_filter])
        return CaptureCommand(args=command)

    if tshark := find_executable("tshark"):
        command = [tshark, "-i", iface, "-a", f"duration:{duration_seconds}", "-w", str(output_path)]
        if bpf_filter:
            command.extend(["-f", bpf_filter])
        return CaptureCommand(args=command)

    if tcpdump := find_executable("tcpdump"):
        command = [tcpdump, "-i", iface, "-U", "-w", "-"]
        if bpf_filter:
            command.extend(bpf_filter.split())
        return CaptureCommand(args=command, stdout_path=output_path, max_duration_seconds=duration_seconds)

    raise CaptureToolError("No capture tool found. Install Wireshark/dumpcap, tshark, or tcpdump.")


def _capture_identifier(iface: str) -> str:
    if " (" in iface and iface.endswith(")"):
        return iface.split(" (", 1)[0]
    return iface
