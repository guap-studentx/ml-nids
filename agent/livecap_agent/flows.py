from __future__ import annotations

import csv
import multiprocessing
import time
from collections.abc import Callable
from pathlib import Path


class FlowCaptureError(RuntimeError):
    pass


DEFAULT_BPF_FILTER = r"ip and (ip proto \tcp or \udp)"

NFSTREAM_COLUMNS = [
    "id",
    "expiration_id",
    "src_ip",
    "src_mac",
    "src_oui",
    "src_port",
    "dst_ip",
    "dst_mac",
    "dst_oui",
    "dst_port",
    "protocol",
    "ip_version",
    "vlan_id",
    "tunnel_id",
    "bidirectional_first_seen_ms",
    "bidirectional_last_seen_ms",
    "bidirectional_duration_ms",
    "bidirectional_packets",
    "bidirectional_bytes",
    "src2dst_first_seen_ms",
    "src2dst_last_seen_ms",
    "src2dst_duration_ms",
    "src2dst_packets",
    "src2dst_bytes",
    "dst2src_first_seen_ms",
    "dst2src_last_seen_ms",
    "dst2src_duration_ms",
    "dst2src_packets",
    "dst2src_bytes",
    "bidirectional_min_ps",
    "bidirectional_mean_ps",
    "bidirectional_stddev_ps",
    "bidirectional_max_ps",
    "src2dst_min_ps",
    "src2dst_mean_ps",
    "src2dst_stddev_ps",
    "src2dst_max_ps",
    "dst2src_min_ps",
    "dst2src_mean_ps",
    "dst2src_stddev_ps",
    "dst2src_max_ps",
    "bidirectional_min_piat_ms",
    "bidirectional_mean_piat_ms",
    "bidirectional_stddev_piat_ms",
    "bidirectional_max_piat_ms",
    "src2dst_min_piat_ms",
    "src2dst_mean_piat_ms",
    "src2dst_stddev_piat_ms",
    "src2dst_max_piat_ms",
    "dst2src_min_piat_ms",
    "dst2src_mean_piat_ms",
    "dst2src_stddev_piat_ms",
    "dst2src_max_piat_ms",
    "bidirectional_syn_packets",
    "bidirectional_cwr_packets",
    "bidirectional_ece_packets",
    "bidirectional_urg_packets",
    "bidirectional_ack_packets",
    "bidirectional_psh_packets",
    "bidirectional_rst_packets",
    "bidirectional_fin_packets",
    "src2dst_syn_packets",
    "src2dst_cwr_packets",
    "src2dst_ece_packets",
    "src2dst_urg_packets",
    "src2dst_ack_packets",
    "src2dst_psh_packets",
    "src2dst_rst_packets",
    "src2dst_fin_packets",
    "dst2src_syn_packets",
    "dst2src_cwr_packets",
    "dst2src_ece_packets",
    "dst2src_urg_packets",
    "dst2src_ack_packets",
    "dst2src_psh_packets",
    "dst2src_rst_packets",
    "dst2src_fin_packets",
]


def capture_flows_csv(
    *,
    iface: str,
    duration_seconds: int,
    output_path: Path,
    bpf_filter: str | None = None,
    should_stop: Callable[[], bool] | None = None,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    error_path = output_path.with_suffix(output_path.suffix + ".error")
    error_path.unlink(missing_ok=True)

    process = multiprocessing.Process(
        target=_nfstream_worker,
        kwargs={
            "iface": iface,
            "duration_seconds": duration_seconds,
            "output_path": output_path,
            "error_path": error_path,
            "bpf_filter": bpf_filter,
        },
    )
    process.start()

    started_at = time.monotonic()
    stopped = False
    try:
        while process.is_alive():
            if should_stop and should_stop():
                stopped = True
                break
            if time.monotonic() - started_at >= duration_seconds:
                stopped = True
                break
            time.sleep(1)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=10)
            if process.is_alive():
                process.kill()
                process.join(timeout=5)

    if error_path.exists():
        message = error_path.read_text(encoding="utf-8", errors="replace").strip()
        error_path.unlink(missing_ok=True)
        raise FlowCaptureError(message or "NFStream flow capture failed")

    if not stopped and process.exitcode not in {0, None}:
        raise FlowCaptureError(f"NFStream flow capture exited with code {process.exitcode}")
    if not output_path.exists() or output_path.stat().st_size == 0:
        raise FlowCaptureError("NFStream produced an empty CSV file")


def _nfstream_worker(
    *,
    iface: str,
    duration_seconds: int,
    output_path: Path,
    error_path: Path,
    bpf_filter: str | None,
) -> None:
    try:
        from nfstream import NFStreamer

        idle_timeout = max(1, min(5, int(duration_seconds)))
        active_timeout = max(1, min(30, int(duration_seconds)))
        streamer = NFStreamer(
            source=iface,
            decode_tunnels=False,
            bpf_filter=bpf_filter or DEFAULT_BPF_FILTER,
            promiscuous_mode=True,
            snapshot_length=1536,
            idle_timeout=idle_timeout,
            active_timeout=active_timeout,
            accounting_mode=0,
            udps=None,
            n_dissections=0,
            statistical_analysis=True,
            splt_analysis=0,
            n_meters=1,
            performance_report=0,
        )

        deadline = time.monotonic() + duration_seconds
        with output_path.open("w", newline="", encoding="utf-8") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=NFSTREAM_COLUMNS)
            writer.writeheader()
            file_obj.flush()

            for flow in streamer:
                writer.writerow({column: getattr(flow, column, "") for column in NFSTREAM_COLUMNS})
                file_obj.flush()
                if time.monotonic() >= deadline:
                    break
    except Exception as exc:
        error_path.write_text(str(exc), encoding="utf-8")
