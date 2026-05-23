from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from src import config


@dataclass
class AnswerCache:
    path: Path = field(default_factory=lambda: Path(config.save_dir) / "agents" / "superagent" / "qa_cache.json")

    def __post_init__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, dict] = self._load()

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save(self) -> None:
        self.path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")

    def get(self, key: str) -> dict | None:
        return self._data.get(key)

    def set(self, key: str, value: dict) -> None:
        self._data[key] = value
        self._save()
