from __future__ import annotations

import shutil
from pathlib import Path


def find_executable(name: str) -> str | None:
    if path := shutil.which(name):
        return path

    windows_candidates = [
        Path("C:/Program Files/Wireshark") / f"{name}.exe",
        Path("C:/Program Files (x86)/Wireshark") / f"{name}.exe",
    ]
    for candidate in windows_candidates:
        if candidate.exists():
            return str(candidate)
    return None
