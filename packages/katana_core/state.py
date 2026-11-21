"""KatanaState — persistent agent state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class KatanaState:
    history: List[Dict[str, Any]] = field(default_factory=list)
    user_settings: Dict[str, Any] = field(default_factory=dict)
    global_metrics: Dict[str, Any] = field(default_factory=dict)
    version: str = "0.2.0-mvp"

    def add_message(self, role: str, content: str, meta: Optional[Dict] = None) -> None:
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": meta or {},
        }
        self.history.append(entry)

    def get_recent(self, n: int = 20) -> List[Dict[str, Any]]:
        return self.history[-n:]

    def update_metric(self, key: str, value: Any) -> None:
        self.global_metrics[key] = value

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "KatanaState":
        path = Path(path)
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            history=data.get("history", []),
            user_settings=data.get("user_settings", {}),
            global_metrics=data.get("global_metrics", {}),
            version=data.get("version", "0.2.0-mvp"),
        )
