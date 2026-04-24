from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    command: list[str]

    @property
    def combined_output(self) -> str:
        return (self.stdout or "") + "\n" + (self.stderr or "")


def run_capture(command: list[str], *, cwd: Path | None = None, timeout: int | None = None) -> CommandResult:
    proc = subprocess.run(command, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout, check=False)
    return CommandResult(proc.returncode, proc.stdout or "", proc.stderr or "", command)


def assert_executable_file(path: str, label: str) -> None:
    if not path:
        raise FileNotFoundError(f"{label} path is empty.")
    p = Path(path).expanduser()
    if p.name == path and not p.exists():
        return
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
