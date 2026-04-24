from __future__ import annotations


def format_timecode(seconds: float) -> str:
    total = int(round(max(0.0, seconds)))
    return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"
