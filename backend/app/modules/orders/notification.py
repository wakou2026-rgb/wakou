from __future__ import annotations
import json
import os

import httpx

from ...core.mailer import send_email

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
    raw = _load_config()
    return {
        "discord_webhook": raw.get("discord_webhook") or raw.get("discord_webhook_url", ""),
        "line_webhook": raw.get("line_webhook") or raw.get("line_notify_token", ""),
        "email_to": raw.get("email_to") or raw.get("email_recipients", ""),
        # Compatibility aliases expected by admin frontend
        "discord_webhook_url": raw.get("discord_webhook_url") or raw.get("discord_webhook", ""),
        "line_notify_token": raw.get("line_notify_token") or raw.get("line_webhook", ""),
        "email_recipients": raw.get("email_recipients") or raw.get("email_to", ""),
    }


def update_config(payload: dict) -> dict:
    config = _load_config()

    normalized = {
        "discord_webhook": payload.get("discord_webhook") or payload.get("discord_webhook_url") or config.get("discord_webhook", ""),
        "line_webhook": payload.get("line_webhook") or payload.get("line_notify_token") or config.get("line_webhook", ""),
        "email_to": payload.get("email_to") or payload.get("email_recipients") or config.get("email_to", ""),
    }
    config.update(normalized)
    _save_config(config)
    return get_config()


async def send_notification(subject: str, body: str, html_body: str | None = None) -> None:
    config = get_config()
    discord_url = config.get("discord_webhook", "") or config.get("discord_webhook_url", "")
    line_value = config.get("line_webhook", "") or config.get("line_notify_token", "")
    email_to = config.get("email_to", "") or config.get("email_recipients", "") or os.getenv("NOTIFY_TO_EMAIL", "")
    if discord_url:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(discord_url, json={"content": f"**{subject}**\n{body}"})
        except Exception:
            pass
    if line_value:
        # Accept either full LINE webhook URL or LINE Notify token.
        line_url = str(line_value)
        line_payload: dict[str, str] = {"message": f"{subject}\n{body}"}
        headers: dict[str, str] = {}
        if not line_url.startswith("http"):
            line_url = "https://notify-api.line.me/api/notify"
            headers = {"Authorization": f"Bearer {line_value}"}
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                await client.post(line_url, headers=headers, data=line_payload)
        except Exception:
            pass
    if email_to:
        try:
            send_email(str(email_to), subject, body, html_body=html_body)
        except Exception:
            pass
