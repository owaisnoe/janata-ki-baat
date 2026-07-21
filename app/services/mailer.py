"""Transactional email via cPanel SMTP (plan §8). Three hops: order
received, payment confirmed, posted-with-proof. Volumes (≤50/day) are far
under shared-host caps.

Dev mode (no SMTP_HOST): messages are logged and written to
instance/outbox/ as .html so the full loop is inspectable offline.
A send failure never breaks the request that triggered it.
"""
import re
import smtplib
import time
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path

from flask import current_app


def _to_text(html):
    text = re.sub(r"<br\s*/?>", "\n", html)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def send_email(to, subject, html):
    cfg = current_app.config
    msg = EmailMessage()
    name, addr = parseaddr(cfg["MAIL_FROM"])
    msg["From"] = formataddr((name, addr)) if name else addr
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(_to_text(html))
    msg.add_alternative(html, subtype="html")

    if not cfg["SMTP_HOST"]:
        outbox = Path(current_app.instance_path) / "outbox"
        outbox.mkdir(parents=True, exist_ok=True)
        slug = re.sub(r"[^a-z0-9]+", "-", subject.lower())[:40]
        (outbox / f"{int(time.time() * 1000)}-{slug}.html").write_text(
            f"<!-- to: {to} -->\n{html}", encoding="utf-8")
        current_app.logger.info("MAIL (dev outbox) to=%s subject=%r", to, subject)
        return True

    try:
        if cfg["SMTP_PORT"] == 465:
            server = smtplib.SMTP_SSL(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15)
        else:
            server = smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15)
            server.starttls()
        with server:
            server.login(cfg["SMTP_USER"], cfg["SMTP_PASS"])
            server.send_message(msg)
        return True
    except Exception:
        current_app.logger.exception("Email send failed to=%s subject=%r",
                                     to, subject)
        return False
