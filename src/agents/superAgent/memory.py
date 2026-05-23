from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src import config


@dataclass
class MemorySnapshot:
    recent_turns: list[dict[str, str]] = field(default_factory=list)
    summary: str = ""


@dataclass
class SuperMemoryStore:
    path: Path = field(default_factory=lambda: Path(config.save_dir) / "agents" / "superagent" / "memory_summary.json")

    def __post_init__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"summaries": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if "summaries" not in data:
                data["summaries"] = {}
            return data
        except Exception:
            return {"summaries": {}}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get_summary(self, thread_id: str) -> str:
        return str(self._data.get("summaries", {}).get(thread_id, ""))

    def update_summary(self, thread_id: str, summary: str) -> None:
        self._data.setdefault("summaries", {})[thread_id] = summary
        self._save()

    def build_snapshot(self, messages, thread_id: str, max_turns: int = 5) -> MemorySnapshot:
        return MemorySnapshot(
            recent_turns=self.extract_recent_turns(messages, max_turns=max_turns),
            summary=self.get_summary(thread_id),
        )

    @staticmethod
    def extract_recent_turns(messages, max_turns: int = 5) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for msg in messages or []:
            role = getattr(msg, "type", "") or msg.__class__.__name__.lower()
            if role not in {"human", "ai", "assistant"}:
                continue

            content = getattr(msg, "content", "")
            if isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False)

            normalized.append(
                {
                    "role": "assistant" if role == "ai" else role,
                    "content": str(content),
                }
            )

        if max_turns <= 0:
            return normalized

        return normalized[-max_turns * 2 :]

    @staticmethod
    def count_human_turns(messages) -> int:
        count = 0
        for msg in messages or []:
            role = getattr(msg, "type", "") or msg.__class__.__name__.lower()
            if role == "human":
                count += 1
        return count
