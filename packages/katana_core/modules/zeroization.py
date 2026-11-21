from __future__ import annotations
import asyncio
from typing import Optional, Callable
from datetime import datetime, timezone, timedelta

class ZeroizationProtocol:
    def __init__(self, threshold_seconds: int = 300, on_wipe: Optional[Callable] = None):
        self.threshold = timedelta(seconds=threshold_seconds)
        self.last_heartbeat: Optional[datetime] = None
        self.on_wipe = on_wipe
        self._wiped = False

    def beat(self) -> None:
        self.last_heartbeat = datetime.now(timezone.utc)
        self._wiped = False

    async def check(self) -> bool:
        if self.last_heartbeat is None:
            return True
        delta = datetime.now(timezone.utc) - self.last_heartbeat
        if delta > self.threshold and not self._wiped:
            self._wiped = True
            if self.on_wipe:
                if asyncio.iscoroutinefunction(self.on_wipe):
                    await self.on_wipe()
                else:
                    self.on_wipe()
            return False
        return True
