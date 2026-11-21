from __future__ import annotations
import asyncio
import os
from typing import List
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class DecoyFile:
    path: str
    content: bytes
    created: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class DynamicHoneypot:
    def __init__(self):
        self.decoys: List[DecoyFile] = []

    async def generate_noise(self, count: int = 10) -> int:
        for i in range(count):
            self.decoys.append(DecoyFile(path=f"/shadow/fake_{i}.dat", content=os.urandom(512)))
            await asyncio.sleep(0.01)
        return len(self.decoys)
