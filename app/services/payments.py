"""Manual UPI payments (plan §8): static QR + upi:// intent link with the
order code in the transaction note; user submits the UTR; admin matches it
against the UPI app. NPCI deprecated UPI Collect (Feb 2026) — QR and intent
links are unaffected, which is why we build on those.
"""
import hashlib
import hmac
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


def razorpay_enabled():
    cfg = current_app.config
    return bool(cfg["RAZORPAY_KEY_ID"] and cfg["RAZORPAY_KEY_SECRET"])


def create_razorpay_order(order):
    """Create a Razorpay order for `order.total` (INR). Returns the Razorpay
    order id, or raises requests.RequestException / ValueError on failure."""
    cfg = current_app.config
    amount_paise = order.total * 100
    if amount_paise < 100:
        raise ValueError("amount below Razorpay minimum (100 paise)")
    resp = requests.post(
        "https://api.razorpay.com/v1/orders",
        auth=(cfg["RAZORPAY_KEY_ID"], cfg["RAZORPAY_KEY_SECRET"]),
        json={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": order.public_code,
            "notes": {"public_code": order.public_code},
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["id"]


def verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, signature):
    """True iff HMAC-SHA256(order_id|payment_id, KEY_SECRET) matches the
    signature Razorpay sent. Constant-time compare."""
    secret = current_app.config["RAZORPAY_KEY_SECRET"]
    if not (secret and razorpay_order_id and razorpay_payment_id and signature):
        return False
    expected = hmac.new(
        secret.encode(),
        f"{razorpay_order_id}|{razorpay_payment_id}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


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
