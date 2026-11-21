"""Telegram Concierge — entry point for Katana Platform."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage

DATA_DIR = Path("/app/data")
MODE_FILE = DATA_DIR / "mode.json"

def _load_mode() -> str:
    if MODE_FILE.exists():
        try:
            return json.loads(MODE_FILE.read_text()).get("mode", "direct")
        except Exception:
            pass
    return "direct"

def _save_mode(mode: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MODE_FILE.write_text(json.dumps({"mode": mode}))

def _parse_ids(raw: str) -> List[int]:
    if not raw.strip():
        return []
    return [int(x.strip()) for x in raw.split(",") if x.strip().isdigit()]

ALLOWED = set(_parse_ids(os.environ.get("TELEGRAM_ALLOWED_USER_IDS", "")))
ADMINS = set(_parse_ids(os.environ.get("TELEGRAM_ADMIN_USER_IDS", "")))
CORE_URL = os.environ.get("KATANA_CORE_URL", "http://katana-core:8000").rstrip("/")
API_TOKEN = os.environ.get("KATANA_API_TOKEN", "")
N8N_URL = os.environ.get("N8N_WEBHOOK_URL", "")
N8N_TOKEN = os.environ.get("N8N_WEBHOOK_TOKEN", "")

bot = Bot(token=os.environ["TELEGRAM_BOT_TOKEN"])
dp = Dispatcher(storage=MemoryStorage())

@dp.message.middleware()
async def allowlist_middleware(handler, event: Message, data):
    uid = event.from_user.id if event.from_user else None
    if uid not in ALLOWED:
        return  # silent drop
    return await handler(event, data)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Katana Concierge online.\n/status /mode /exec")

@dp.message(Command("status"))
async def cmd_status(message: Message):
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.get(f"{CORE_URL}/health")
            data = r.json()
            await message.answer(f"Core: {data.get('status')} | node={data.get('node_id')} | mode={_load_mode()}")
        except Exception as e:
            await message.answer(f"Core unreachable: {e}")

@dp.message(Command("mode"))
async def cmd_mode(message: Message):
    if message.from_user.id not in ADMINS:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or parts[1].strip() not in ("n8n", "direct"):
        await message.answer(f"Current mode: {_load_mode()}\nUsage: /mode n8n | direct")
        return
    mode = parts[1].strip()
    _save_mode(mode)
    await message.answer(f"Mode set to: {mode}")

@dp.message(Command("exec"))
async def cmd_exec(message: Message):
    if message.from_user.id not in ADMINS:
        return
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /exec <command_id>\n(e.g. uptime, df, docker_ps)")
        return
    command_id = parts[1].strip()
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(
            f"{CORE_URL}/v1/execute",
            json={"action": "ssh", "payload": {"command_id": command_id}},
            headers={"X-API-Token": API_TOKEN},
        )
        data = r.json()
        result = data.get("result", {})
        out = result.get("stdout") or result.get("stderr") or str(data)
        await message.answer(out[:3500] or "(empty)")

@dp.message(F.text | F.voice)
async def handle_message(message: Message):
    mode = _load_mode()
    if mode == "direct":
        text = message.text or "[voice]"
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                f"{CORE_URL}/v1/execute",
                json={"action": "ingest", "payload": {"source": "telegram", "data": text}},
                headers={"X-API-Token": API_TOKEN},
            )
            data = r.json()
            await message.answer(f"direct ok | entities={data.get('entities')}")
    else:
        if not N8N_URL:
            await message.answer("N8N_WEBHOOK_URL not set")
            return
        headers = {"Authorization": f"Bearer {N8N_TOKEN}"} if N8N_TOKEN else {}
        async with httpx.AsyncClient(timeout=60) as client:
            if message.voice:
                file = await bot.get_file(message.voice.file_id)
                url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
                audio = await client.get(url)
                files = {"file": ("voice.ogg", audio.content, "audio/ogg")}
                data = {"chat_id": str(message.chat.id), "user_id": str(message.from_user.id)}
                r = await client.post(N8N_URL, data=data, files=files, headers=headers)
            else:
                r = await client.post(
                    N8N_URL,
                    json={"text": message.text, "chat_id": message.chat.id, "user_id": message.from_user.id},
                    headers=headers,
                )
            await message.answer("n8n accepted" if r.is_success else f"n8n error {r.status_code}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
