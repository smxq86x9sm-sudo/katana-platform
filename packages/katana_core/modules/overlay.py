from __future__ import annotations
import asyncio
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class OverlayNode:
    node_id: str
    trusted: bool = False

class SecureOverlay:
    def __init__(self):
        self.peers: Dict[str, OverlayNode] = {}
        self._running = False

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def announce(self, node_id: str, sealed_payload: bytes) -> bool:
        if not self._running:
            return False
        self.peers[node_id] = OverlayNode(node_id=node_id, trusted=True)
        return True
