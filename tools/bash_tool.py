from __future__ import annotations

import subprocess
import time
from typing import Any

from core.session_log import now_iso


def run_bash(command: str, working_directory: str, timeout_seconds: int) -> dict[str, Any]:
    started = now_iso()
    started_mono = time.monotonic()
    result = subprocess.run(
        command,
        cwd=working_directory,
        shell=True,
        text=True,
        capture_output=True,
        timeout=timeout_seconds,
        check=False,
    )
    finished = now_iso()
    return {
        "type": "tool",
        "tool": "bash",
        "command": command,
        "started": started,
        "finished": finished,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.returncode,
        "duration_ms": int((time.monotonic() - started_mono) * 1000),
    }

