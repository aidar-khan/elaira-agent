from __future__ import annotations

import subprocess
from pathlib import Path


class GitManager:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _is_repo_root(self) -> bool:
        return (self.root / ".git").exists()

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            check=False,
        )

    def git_status(self) -> dict[str, str | int]:
        if not self._is_repo_root():
            return {"stdout": "", "stderr": "Repository is not initialized at agent root.", "exit_code": 0}
        result = self._run("status", "--short")
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}

    def auto_commit_after_turn(self, summary: str) -> dict[str, str | int]:
        if not self._is_repo_root():
            return {"stdout": "Skipping git commit because agent root is not a standalone git repository.", "stderr": "", "exit_code": 0}
        add_result = self._run("add", ".")
        if add_result.returncode != 0:
            return {"stdout": add_result.stdout, "stderr": add_result.stderr, "exit_code": add_result.returncode}
        status = self._run("status", "--short")
        if not status.stdout.strip():
            return {"stdout": "No changes to commit.", "stderr": "", "exit_code": 0}
        commit = self._run("commit", "-m", f"turn: {summary[:72]}")
        return {"stdout": commit.stdout, "stderr": commit.stderr, "exit_code": commit.returncode}

    def git_push(self) -> dict[str, str | int]:
        if not self._is_repo_root():
            return {"stdout": "", "stderr": "Repository is not initialized at agent root.", "exit_code": 0}
        result = self._run("push")
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
