from __future__ import annotations

import time

import httpx

from livecap_agent.capture import capture_pcap
from livecap_agent.client import AgentApiClient
from livecap_agent.config import parse_config
from livecap_agent.interfaces import list_interfaces
from livecap_agent.metadata import collect_metadata
from livecap_agent.storage import cleanup_pcap_files, remove_file_quietly


def run_once(client: AgentApiClient) -> dict:
    return client.send_heartbeat(interfaces=list_interfaces(), metadata=collect_metadata())


def main() -> None:
    config = parse_config()
    client = AgentApiClient(backend_url=config.backend_url, agent_id=config.agent_id, token=config.token)
    cleanup_pcap_files(
        config.work_dir,
        max_files=config.max_pcap_files,
        max_age_hours=config.pcap_retention_hours,
    )
    print(f"livecap-agent started: backend={config.backend_url} agent_id={config.agent_id}")

    while True:
        try:
            response = run_once(client)
            print(f"heartbeat ok: status={response['status']} last_seen_at={response['last_seen_at']}")
            for command in client.get_commands():
                handle_command(client, config, command)
            cleanup_pcap_files(
                config.work_dir,
                max_files=config.max_pcap_files,
                max_age_hours=config.pcap_retention_hours,
            )
        except httpx.HTTPStatusError as exc:
            print(f"heartbeat failed: http={exc.response.status_code} detail={exc.response.text}")
        except httpx.HTTPError as exc:
            print(f"heartbeat failed: {exc}")

        if config.once:
            return
        time.sleep(config.interval_seconds)


def handle_command(client: AgentApiClient, config, command: dict) -> None:
    command_type = command.get("type", "capture")
    if command_type == "live_session":
        handle_live_session_command(client, config, command)
        return
    if command_type != "capture":
        print(f"unsupported command type: {command_type}")
        return

    capture_id = command["capture_id"]
    output_path = config.work_dir / f"{capture_id}.pcap"
    print(
        "capture command: "
        f"capture_id={capture_id} iface={command['iface']} duration={command['duration_seconds']}s"
    )
    try:
        capture_pcap(
            iface=command["iface"],
            duration_seconds=command["duration_seconds"],
            output_path=output_path,
            bpf_filter=command.get("bpf_filter"),
            should_stop=lambda: client.capture_status(capture_id=capture_id) == "stopping",
        )
        client.upload_pcap(capture_id=capture_id, pcap_path=output_path)
        print(f"capture uploaded: capture_id={capture_id} file={output_path}")
        if not config.keep_pcaps:
            remove_file_quietly(output_path)
    except Exception as exc:
        message = str(exc)[:2000]
        print(f"capture failed: capture_id={capture_id} error={message}")
        client.fail_capture(capture_id=capture_id, error_message=message)


def handle_live_session_command(client: AgentApiClient, config, command: dict) -> None:
    live_session_id = command["live_session_id"]
    chunk_seconds = int(command.get("chunk_seconds") or 15)
    duration_seconds = int(command["duration_seconds"])
    started_at = time.monotonic()
    chunk_index = 1
    print(
        "live session started: "
        f"live_session_id={live_session_id} iface={command['iface']} "
        f"chunk={chunk_seconds}s duration={duration_seconds}s"
    )
    try:
        while True:
            status = client.live_session_status(live_session_id=live_session_id)
            if status in {"stopping", "stopped", "failed", "completed"}:
                break

            elapsed = time.monotonic() - started_at
            remaining = duration_seconds - int(elapsed)
            if remaining <= 0:
                break

            current_chunk_seconds = min(chunk_seconds, remaining)
            output_path = config.work_dir / f"{live_session_id}_chunk_{chunk_index:04d}.pcap"
            print(
                "live chunk capture: "
                f"live_session_id={live_session_id} chunk={chunk_index} duration={current_chunk_seconds}s"
            )
            capture_pcap(
                iface=command["iface"],
                duration_seconds=current_chunk_seconds,
                output_path=output_path,
                bpf_filter=command.get("bpf_filter"),
                should_stop=lambda: client.live_session_status(live_session_id=live_session_id) == "stopping",
            )
            status = client.live_session_status(live_session_id=live_session_id)
            if status in {"stopped", "failed", "completed"}:
                break
            client.upload_live_session_chunk(live_session_id=live_session_id, pcap_path=output_path)
            print(f"live chunk uploaded: live_session_id={live_session_id} chunk={chunk_index} file={output_path}")
            if not config.keep_pcaps:
                remove_file_quietly(output_path)
            cleanup_pcap_files(
                config.work_dir,
                max_files=config.max_pcap_files,
                max_age_hours=config.pcap_retention_hours,
            )
            chunk_index += 1

        client.complete_live_session(live_session_id=live_session_id)
        print(f"live session completed: live_session_id={live_session_id} chunks={chunk_index - 1}")
    except Exception as exc:
        message = str(exc)[:2000]
        try:
            status = client.live_session_status(live_session_id=live_session_id)
        except Exception:
            status = "unknown"
        if status == "stopping":
            client.complete_live_session(live_session_id=live_session_id)
            print(f"live session stopped: live_session_id={live_session_id}")
            return
        print(f"live session failed: live_session_id={live_session_id} error={message}")
        client.fail_live_session(live_session_id=live_session_id, error_message=message)


if __name__ == "__main__":
    main()
