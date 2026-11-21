# Katana Platform MVP

Minimal working stack: **Katana Core** + **SSH Bridge** + **Telegram Concierge** + cleaned n8n workflows.

## Quick start

```bash
cp .env.example .env
# fill secrets
docker compose up -d --build
```

One command. Internal network only for core and ssh-bridge.

## Services

| Service | Port | Network | Role |
|---------|------|---------|------|
| katana-core | 8000 (internal) | backend | State, crypto, actions |
| ssh-bridge | 8001 (internal) | backend | Whitelisted remote exec |
| telegram-concierge | — | backend + egress | Bot entry point |
| n8n (optional) | 127.0.0.1:5678 | backend + egress | Workflows |

## Telegram commands

- `/start` — hello
- `/status` — core health + node_id
- `/mode n8n|direct` — switch routing (admin only, persisted)
- `/exec <command_id>` — run allowed SSH command (admin only)

## Auth

All internal calls use `X-API-Token`.  
Telegram middleware drops any user not in `TELEGRAM_ALLOWED_USER_IDS`.
