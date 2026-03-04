from __future__ import annotations

from email.message import EmailMessage
import os
import smtplib
import ssl


def _smtp_config() -> dict[str, str | int | float | bool]:
    host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    port = int(os.getenv("SMTP_PORT", "465"))
    username = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_APP_PASSWORD", "").strip()
    sender = os.getenv("MAIL_FROM", username).strip()
    timeout = float(os.getenv("SMTP_TIMEOUT_SECONDS", "12"))
    enabled = bool(host and port and username and password and sender)
    return {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "sender": sender,
        "timeout": timeout,
        "enabled": enabled,
    }


def build_html_email(
    subject: str,
    preheader: str = "Wakou Notification",
    content: str = "",
    fields: dict[str, str] | None = None,
    actions: list[dict[str, str]] | None = None,
    footer_text: str = "本郵件由 Wakou 系統自動送出。請勿直接回覆。"
) -> str:
    """Builds a beautiful, responsive HTML email template."""
    html = [
        "<div style='font-family:\"Helvetica Neue\", Helvetica, Arial, \"PingFang TC\", \"Heiti TC\", \"Microsoft JhengHei\", sans-serif;max-width:680px;margin:0 auto;background:#f7f5f1;padding:32px 20px;'>",
        "<div style='background:#ffffff;border:1px solid #e8e0d3;border-radius:12px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.03);'>",
        "<div style='background:linear-gradient(135deg, #1e293b, #0f172a);color:#ffffff;padding:24px 32px;'>",
        f"<h2 style='margin:0;font-size:22px;font-weight:600;letter-spacing:0.5px;'>{subject}</h2>",
        f"<p style='margin:8px 0 0;font-size:13px;color:#cbd5e1;letter-spacing:1px;'>{preheader.upper()}</p>",
        "</div>",
        "<div style='padding:32px;'>",
    ]

    if content:
        content_html = content.replace('\n', '<br>')
        html.append(f"<div style='color:#334155;line-height:1.6;font-size:15px;margin-bottom:24px;'>{content_html}</div>")

    if fields:
        html.append("<div style='background:#f8fafc;border-radius:8px;padding:20px;margin-bottom:24px;border:1px solid #f1f5f9;'>")
        html.append("<table width='100%' cellpadding='0' cellspacing='0' style='font-size:14px;line-height:1.6;'>")
        for k, v in fields.items():
            html.append(f"<tr><td style='padding:8px 0;color:#64748b;width:120px;vertical-align:top;font-weight:500;'>{k}</td><td style='padding:8px 0;color:#0f172a;vertical-align:top;font-weight:600;'>{v}</td></tr>")
        html.append("</table></div>")

    if actions:
        html.append("<div style='display:flex;gap:12px;flex-wrap:wrap;margin-top:32px;'>")
        for idx, act in enumerate(actions):
            label = act.get('label', 'Click Here')
            url = act.get('url', '#')
            # First button: Gold (#b29262), secondary: Slate (#334155)
            bg = "#b29262" if idx == 0 else "#334155"
            color = "#ffffff"
            html.append(f"<a href='{url}' style='display:inline-block;background:{bg};color:{color};text-decoration:none;padding:12px 24px;border-radius:6px;font-weight:600;font-size:14px;text-align:center;'>{label}</a>")
        html.append("</div>")

    html.append("</div></div>")
    html.append(f"<p style='margin:20px 0 0;color:#94a3b8;font-size:12px;text-align:center;line-height:1.5;'>{footer_text}</p>")
    html.append("</div>")

    return "".join(html)


def send_email(to_email: str, subject: str, body: str, html_body: str | None = None) -> tuple[bool, str]:
    cfg = _smtp_config()
    if not cfg["enabled"]:
        return False, "smtp-not-configured"

    message = EmailMessage()
    message["From"] = str(cfg["sender"])
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    if html_body:
        message.add_alternative(html_body, subtype="html")

    context = ssl.create_default_context()
    try:
        if int(cfg["port"]) == 465:
            # SSL 直連（port 465）
            with smtplib.SMTP_SSL(str(cfg["host"]), 465, context=context, timeout=float(cfg["timeout"])) as server:
                server.login(str(cfg["username"]), str(cfg["password"]))
                server.send_message(message)
        else:
            # STARTTLS（port 587）
            with smtplib.SMTP(str(cfg["host"]), int(cfg["port"]), timeout=float(cfg["timeout"])) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(str(cfg["username"]), str(cfg["password"]))
                server.send_message(message)
        return True, "sent"
    except smtplib.SMTPAuthenticationError:
        return False, "smtp-auth-failed"
    except smtplib.SMTPResponseException as exc:
        return False, f"smtp-{exc.smtp_code}"
    except Exception:
        return False, "smtp-send-failed"
