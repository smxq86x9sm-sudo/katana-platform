from __future__ import annotations
import asyncio
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

@dataclass
class SiphonResult:
    entities: List[str] = field(default_factory=list)
    clusters: Dict[str, List[str]] = field(default_factory=dict)
    anomalies: List[str] = field(default_factory=list)

class KnowledgeSiphon:
    def __init__(self):
        self._index: Dict[str, Any] = {}

    async def ingest(self, source: str, payload: Any) -> SiphonResult:
        await asyncio.sleep(0.01)
        text = str(payload)[:500]
        result = SiphonResult(entities=["entity_stub"], clusters={"default": [text[:80]]}, anomalies=[])
        self._index[source] = result
        return result
