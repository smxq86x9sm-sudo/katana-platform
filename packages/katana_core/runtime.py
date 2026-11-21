"""Katana MVP Runtime."""

from __future__ import annotations

import os
from .state import KatanaState
from .crypto_channel import SecureChannel
from .modules.siphon import KnowledgeSiphon
from .modules.overlay import SecureOverlay
from .modules.honeypot import DynamicHoneypot
from .modules.zeroization import ZeroizationProtocol


class KatanaRuntime:
    def __init__(self, master_secret: bytes | None = None):
        self.secret = master_secret or os.urandom(32)
        self.state = KatanaState.load("data/katana_state.json")
        self.channel = SecureChannel(self.secret)
        self.siphon = KnowledgeSiphon()
        self.overlay = SecureOverlay()
        self.honeypot = DynamicHoneypot()
        self.zero = ZeroizationProtocol(threshold_seconds=300)

    async def boot(self) -> None:
        self.state.add_message("system", "Katana MVP boot")
        self.state.update_metric("boots", self.state.global_metrics.get("boots", 0) + 1)
        self.state.save("data/katana_state.json")
        await self.overlay.start()
        self.zero.beat()
        sealed = self.channel.heartbeat()
        await self.overlay.announce(self.channel.state.node_id, sealed)

    async def shutdown(self) -> None:
        await self.overlay.stop()
        self.state.add_message("system", "Katana MVP shutdown")
        self.state.save("data/katana_state.json")
