from __future__ import annotations

import time
from pathlib import Path


def remove_file_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def cleanup_pcap_files(work_dir: Path, *, max_files: int, max_age_hours: float) -> None:
    if not work_dir.exists():
        return

    pcaps = sorted(
        [path for path in work_dir.glob("*.pcap") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    for path in pcaps[max_files:]:
        remove_file_quietly(path)

    for path in pcaps[:max_files]:
        try:
            age_seconds = now - path.stat().st_mtime
        except OSError:
            continue
        if age_seconds > max_age_seconds:
            remove_file_quietly(path)
