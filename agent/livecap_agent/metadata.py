from __future__ import annotations

import platform


def collect_metadata() -> dict[str, str]:
    return {
        "hostname": platform.node(),
        "os": platform.platform(),
        "python": platform.python_version(),
    }
