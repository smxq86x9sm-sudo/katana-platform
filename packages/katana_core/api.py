"""Katana Core FastAPI layer."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from runtime import KatanaRuntime
from state import KatanaState


class ExecuteRequest(BaseModel):
    action: str = Field(..., description="heartbeat | ingest | noise | check_zero | ssh")
    payload: Dict[str, Any] = Field(default_factory=dict)


class StateResponse(BaseModel):
    version: str
    history_len: int
    recent: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    node_id: str


_runtime: Optional[KatanaRuntime] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _runtime
    secret = os.environ.get("KATANA_MASTER_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("KATANA_MASTER_SECRET must be set and >= 32 characters")
    _runtime = KatanaRuntime(master_secret=secret.encode("utf-8"))
    await _runtime.boot()
    yield
    if _runtime:
        await _runtime.shutdown()


app = FastAPI(title="Katana Core API", version="0.2.0", lifespan=lifespan)


def _require_token(x_api_token: Optional[str] = Header(None, alias="X-API-Token")) -> None:
    expected = os.environ.get("KATANA_API_TOKEN")
    if not expected:
        raise HTTPException(status_code=500, detail="KATANA_API_TOKEN not configured")
    if not x_api_token or x_api_token != expected:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid or missing X-API-Token")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "katana-core",
        "node_id": _runtime.channel.state.node_id if _runtime else None,
    }


@app.get("/v1/state", response_model=StateResponse)
async def get_state(x_api_token: Optional[str] = Header(None, alias="X-API-Token")):
    _require_token(x_api_token)
    if not _runtime:
        raise HTTPException(status_code=503, detail="Runtime not ready")
    state: KatanaState = _runtime.state
    return StateResponse(
        version=state.version,
        history_len=len(state.history),
        recent=state.get_recent(10),
        metrics=state.global_metrics,
        node_id=_runtime.channel.state.node_id,
    )


@app.post("/v1/execute")
async def execute(
    body: ExecuteRequest,
    x_api_token: Optional[str] = Header(None, alias="X-API-Token"),
):
    _require_token(x_api_token)
    if not _runtime:
        raise HTTPException(status_code=503, detail="Runtime not ready")

    action = body.action.lower().strip()
    payload = body.payload or {}

    if action == "heartbeat":
        sealed = _runtime.channel.heartbeat()
        return {"ok": True, "action": "heartbeat", "sealed_bytes": len(sealed)}

    if action == "ingest":
        source = str(payload.get("source", "api"))
        data = payload.get("data", payload)
        result = await _runtime.siphon.ingest(source, data)
        return {"ok": True, "action": "ingest", "entities": result.entities, "clusters": result.clusters}

    if action == "noise":
        count = int(payload.get("count", 5))
        n = await _runtime.honeypot.generate_noise(count)
        return {"ok": True, "action": "noise", "decoys": n}

    if action == "check_zero":
        alive = await _runtime.zero.check()
        return {"ok": True, "action": "check_zero", "alive": alive}

    if action == "ssh":
        command_id = str(payload.get("command_id", "")).strip()
        if not command_id:
            raise HTTPException(status_code=400, detail="payload.command_id required for action=ssh")
        bridge_url = os.environ.get("SSH_BRIDGE_URL", "http://ssh-bridge:8001")
        token = os.environ.get("KATANA_API_TOKEN", "")
        async with httpx.AsyncClient(timeout=40.0) as client:
            r = await client.post(
                f"{bridge_url}/execute",
                json={"command_id": command_id},
                headers={"X-API-Token": token},
            )
            return {"ok": r.is_success, "action": "ssh", "bridge_status": r.status_code, "result": r.json()}

    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
