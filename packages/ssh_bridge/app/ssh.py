import asyncio
import io
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict

import paramiko
from .config import settings

logger = logging.getLogger("ssh_bridge.ssh")

# Strict registry: command_id -> exact shell command (no free-form shell)
COMMAND_REGISTRY: Dict[str, str] = {
    "uptime": "uptime",
    "uname": "uname -a",
    "df": "df -h",
    "free": "free -h",
    "whoami": "whoami",
    "id": "id",
    "hostname": "hostname",
    "date": "date",
    "pwd": "pwd",
    "ps": "ps aux --sort=-%mem | head -20",
    "docker_ps": "docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'",
}

_executor = ThreadPoolExecutor(max_workers=4)


def get_ssh_key() -> paramiko.PKey:
    if settings.SSH_KEY_CONTENT:
        key_str = settings.SSH_KEY_CONTENT.strip()
        for key_class in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
            try:
                return key_class.from_private_key(io.StringIO(key_str))
            except Exception:
                continue
        raise ValueError("Failed to parse SSH_KEY_CONTENT")
    if not settings.SSH_KEY_PATH:
        raise ValueError("Neither SSH_KEY_CONTENT nor SSH_KEY_PATH is set")
    for key_class in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            return key_class.from_private_key_file(settings.SSH_KEY_PATH)
        except Exception:
            continue
    raise ValueError(f"Failed to load SSH key from {settings.SSH_KEY_PATH}")


def _execute_sync(command: str) -> dict:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.load_host_keys(settings.SSH_KNOWN_HOSTS)
    except Exception as e:
        logger.warning("known_hosts load: %s", e)
    try:
        pkey = get_ssh_key()
        client.connect(
            hostname=settings.SSH_HOST,
            port=settings.SSH_PORT,
            username=settings.SSH_USER,
            pkey=pkey,
            timeout=15,
            allow_agent=False,
            look_for_keys=False,
        )
        stdin, stdout, stderr = client.exec_command(command, timeout=settings.COMMAND_TIMEOUT)
        max_b = settings.MAX_OUTPUT_BYTES
        out_bytes = stdout.read(max_b + 1)
        err_bytes = stderr.read(max_b + 1)
        exit_status = stdout.channel.recv_exit_status()
        truncated = len(out_bytes) > max_b or len(err_bytes) > max_b
        out_bytes = out_bytes[:max_b]
        err_bytes = err_bytes[:max_b]
        stdout_str = out_bytes.decode("utf-8", errors="replace")
        stderr_str = err_bytes.decode("utf-8", errors="replace")
        if truncated:
            stderr_str += "\n[output truncated]"
        return {"success": True, "exit_code": exit_status, "stdout": stdout_str, "stderr": stderr_str}
    except Exception as e:
        logger.exception("SSH failed")
        return {"success": False, "exit_code": -1, "stdout": "", "stderr": str(e)}
    finally:
        client.close()


async def execute_by_id(command_id: str) -> dict:
    cmd = COMMAND_REGISTRY.get(command_id)
    if not cmd:
        return {
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Unknown command_id '{command_id}'. Allowed: {sorted(COMMAND_REGISTRY.keys())}",
        }
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(_executor, _execute_sync, cmd)
