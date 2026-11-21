"""Katana Secure Crypto Channel — AES-GCM + HMAC fallback."""

from __future__ import annotations

import hashlib
import hmac
import os
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def derive_key(secret: bytes, salt: bytes, purpose: str = "katana-channel") -> bytes:
    return hmac.new(secret, salt + purpose.encode(), hashlib.sha256).digest()


def seal(data: bytes, key: bytes) -> bytes:
    if HAS_CRYPTOGRAPHY and len(key) >= 32:
        aesgcm = AESGCM(key[:32])
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, data, None)
        return b"\x01" + nonce + ct
    digest = hmac.new(key, data, hashlib.sha256).digest()
    return b"\x00" + digest + data


def unseal(sealed: bytes, key: bytes) -> Optional[bytes]:
    if len(sealed) < 33:
        return None
    version = sealed[0]
    if version == 1 and HAS_CRYPTOGRAPHY and len(key) >= 32:
        nonce, ct = sealed[1:13], sealed[13:]
        try:
            aesgcm = AESGCM(key[:32])
            return aesgcm.decrypt(nonce, ct, None)
        except Exception:
            return None
    mac, payload = sealed[1:33], sealed[33:]
    expected = hmac.new(key, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(mac, expected):
        return None
    return payload


@dataclass
class CryptoChannelState:
    node_id: str = ""
    peer_keys: Dict[str, str] = field(default_factory=dict)
    session_nonces: Dict[str, str] = field(default_factory=dict)
    last_proof_of_life: Optional[str] = None
    version: str = "0.2.0-mvp"

    def mark_alive(self) -> None:
        self.last_proof_of_life = _utc_now()

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(asdict(self), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "CryptoChannelState":
        path = Path(path)
        if not path.exists():
            return cls()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class SecureChannel:
    def __init__(self, master_secret: bytes, state_path: str | Path = "data/crypto_channel.json"):
        if len(master_secret) < 32:
            raise ValueError("master_secret must be >= 32 bytes")
        self.master = master_secret
        self.state_path = Path(state_path)
        self.state = CryptoChannelState.load(self.state_path)
        if not self.state.node_id:
            self.state.node_id = hashlib.sha256(os.urandom(32)).hexdigest()[:16]
            self.state.save(self.state_path)

    def seal_payload(self, payload: Dict[str, Any], purpose: str = "pol") -> bytes:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
        key = derive_key(self.master, self.state.node_id.encode(), purpose)
        return seal(raw, key)

    def unseal_payload(self, sealed: bytes, purpose: str = "pol") -> Optional[Dict[str, Any]]:
        key = derive_key(self.master, self.state.node_id.encode(), purpose)
        raw = unseal(sealed, key)
        if raw is None:
            return None
        try:
            return json.loads(raw.decode())
        except Exception:
            return None

    def heartbeat(self) -> bytes:
        self.state.mark_alive()
        self.state.save(self.state_path)
        packet = {
            "type": "proof_of_life",
            "node": self.state.node_id,
            "ts": self.state.last_proof_of_life,
            "v": self.state.version,
        }
        return self.seal_payload(packet, purpose="pol")
