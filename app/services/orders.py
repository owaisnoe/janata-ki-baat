"""Shared order-confirmation logic.

One code path for turning a paid order into a confirmed Letter #, so the
manual admin-confirm route and the automatic Razorpay-verify route can never
drift apart: same serial assignment, same ledger entries, same email.
"""
from flask import current_app, render_template, url_for

from ..extensions import db
from ..models import LedgerEntry, utcnow
from . import mailer
from .util import next_serial, promised_post_date


def confirm_order(order):
    """Mark a paid order confirmed: assign serial, write ledger, email the
    sender. Idempotent — a second call on an already-confirmed order is a
    no-op (guards against a double Razorpay callback). Caller commits."""
    if order.status not in ("pending_payment", "utr_submitted"):
        return False

    order.status = "confirmed"
    order.confirmed_at = utcnow()
    order.serial_no = next_serial()
    order.promised_date = promised_post_date()

    if order.sponsored_request:
        tier_price = current_app.config["TIERS"][order.tier]["price"]
        db.session.add(LedgerEntry(type="fund", amount=-tier_price,
                                   order_ref=order.public_code,
                                   note="sponsored letter (fund draw)"))
    else:
        db.session.add(LedgerEntry(type="fee", amount=order.amount,
                                   order_ref=order.public_code,
                                   note=f"{order.tier} fee"))
        if order.tip:
            db.session.add(LedgerEntry(type="tip", amount=order.tip,
                                       order_ref=order.public_code,
                                       note="chai for the volunteer"))
    db.session.commit()

    status_url = current_app.config["BASE_URL"] + url_for(
        "public.status", code=order.public_code)
    mailer.send_email(
        order.email,
        f"Payment confirmed — you are Letter #{order.serial_no:,}",
        render_template("emails/payment_confirmed.html", order=order,
                        status_url=status_url),
    )
    return True


def confirm_sponsorship(s):
    """Mark a paid sponsorship confirmed: money into the Letters Fund + receipt
    email. Idempotent — a replayed Razorpay callback is a no-op. Caller commits
    (the ledger add is committed here so fund_balance reflects it immediately)."""
    if s.status not in ("pending_payment", "utr_submitted"):
        return False
    s.status, s.confirmed_at = "confirmed", utcnow()
    db.session.add(LedgerEntry(type="fund", amount=s.amount,
                               order_ref=s.public_code,
                               note=f"sponsored {s.bundle_qty} letter(s)"))
    db.session.commit()
    mailer.send_email(
        s.email, f"Receipt — you sponsored {s.bundle_qty} letter(s)",
        render_template("emails/sponsor_receipt.html", s=s),
    )
    return True
