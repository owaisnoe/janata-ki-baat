"""Manual UPI payments (plan §8): static QR + upi:// intent link with the
order code in the transaction note; user submits the UTR; admin matches it
against the UPI app. NPCI deprecated UPI Collect (Feb 2026) — QR and intent
links are unaffected, which is why we build on those.
"""
import io
from urllib.parse import quote

import qrcode
import requests
from flask import current_app


def upi_uri(order):
    cfg = current_app.config
    pa = cfg["UPI_VPA"]
    pn = quote(cfg["UPI_PAYEE_NAME"])
    tn = quote(f"{order.public_code} Janata Ki Baat")
    return f"upi://pay?pa={pa}&pn={pn}&am={order.total}&cu=INR&tn={tn}"


def qr_png(order):
    img = qrcode.make(upi_uri(order), box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def verify_turnstile(token, remote_ip=None):
    """True when the Turnstile check passes — or when Turnstile isn't
    configured (local dev / pre-Cloudflare)."""
    secret = current_app.config["TURNSTILE_SECRET_KEY"]
    if not secret:
        return True
    if not token:
        return False
    try:
        resp = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": secret, "response": token, "remoteip": remote_ip},
            timeout=5,
        )
        return bool(resp.json().get("success"))
    except requests.RequestException:
        current_app.logger.exception("Turnstile verify failed")
        # Fail open: a Cloudflare hiccup must not block lawful letters;
        # Flask-Limiter still rate-limits the endpoint underneath.
        return True
