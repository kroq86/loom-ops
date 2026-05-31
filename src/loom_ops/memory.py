from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_PROMPT_BYTES = 4096
DEFAULT_RECENT_LIMIT = 20


@dataclass(frozen=True)
class MemoryStore:
    path: Path

    @classmethod
    def for_workspace(cls, workspace: Path) -> MemoryStore:
        directory = workspace / ".loom-ops"
        directory.mkdir(parents=True, exist_ok=True)
        return cls(path=directory / "memory.jsonl")

    def append(self, entry: dict[str, Any]) -> None:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            **entry,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def recent(self, limit: int = DEFAULT_RECENT_LIMIT) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        lines = self.path.read_text(encoding="utf-8").splitlines()
        entries: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            if line.strip():
                entries.append(json.loads(line))
        return entries

    def format_for_prompt(self, limit: int = DEFAULT_RECENT_LIMIT) -> str:
        entries = self.recent(limit=limit)
        if not entries:
            return ""
        lines = []
        for entry in entries:
            kind = entry.get("kind", "note")
            summary = entry.get("summary", "")
            lines.append(f"- [{kind}] {summary}")
        text = "Prior ops context:\n" + "\n".join(lines)
        if len(text.encode("utf-8")) > MAX_PROMPT_BYTES:
            text = text.encode("utf-8")[:MAX_PROMPT_BYTES].decode("utf-8", errors="ignore")
            text += "\n... [truncated]"
        return text
