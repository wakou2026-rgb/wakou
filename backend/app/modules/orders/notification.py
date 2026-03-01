from __future__ import annotations
import json
import os

import httpx

# Simple file-based config (Docker volume persistent)
_CONFIG_PATH = os.getenv("NOTIFICATION_CONFIG_PATH", "/tmp/wakou_notifications.json")


def _load_config() -> dict:
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(config: dict) -> None:
    with open(_CONFIG_PATH, "w") as f:
        json.dump(config, f)


def get_config() -> dict:
    return _load_config()


def update_config(payload: dict) -> dict:
    config = _load_config()
    config.update(
        {k: v for k, v in payload.items() if k in {"line_webhook", "discord_webhook", "email_to"}}
    )
    _save_config(config)
    return config


async def send_notification(subject: str, body: str) -> None:
    config = _load_config()
    discord_url = config.get("discord_webhook", "")
    line_url = config.get("line_webhook", "")
    if discord_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(discord_url, json={"content": f"**{subject}**\n{body}"})
        except Exception:
            pass
    if line_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(line_url, json={"message": f"{subject}\n{body}"})
        except Exception:
            pass
