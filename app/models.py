from datetime import datetime, timezone

from .extensions import db


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Order(db.Model):
    __tablename__ = "orders"

    # Status flow: pending_payment -> utr_submitted -> confirmed -> printed
    #              -> posted -> delivered   (terminal: expired, refunded)
    STATUSES = [
        "pending_payment",
        "utr_submitted",
        "confirmed",
        "printed",
        "posted",
        "delivered",
        "expired",
        "refunded",
    ]

    id = db.Column(db.Integer, primary_key=True)
    public_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    # Serial number = the public "Letter #1,247" count; assigned on payment
    # confirmation so the counter only ever shows real letters.
    serial_no = db.Column(db.Integer, unique=True, nullable=True)

    name = db.Column(db.String(120), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    phone = db.Column(db.String(20), nullable=True)

    template_id = db.Column(db.Integer, db.ForeignKey("templates.id"), nullable=False)
    personal_para = db.Column(db.Text, nullable=True)
    # Optional postal address if the sender wants a ministry reply.
    # DPDP hygiene: purged 30 days after delivery (scripts/purge_addresses.py).
    reply_address = db.Column(db.Text, nullable=True)

    tier = db.Column(db.String(20), nullable=False)  # speedpost | epost
    amount = db.Column(db.Integer, nullable=False)   # tier price, ₹
    tip = db.Column(db.Integer, nullable=False, default=0)

    status = db.Column(db.String(20), nullable=False, default="pending_payment",
                       index=True)
    utr = db.Column(db.String(40), nullable=True)
    # Razorpay: order id created server-side, payment id returned on success.
    razorpay_order_id = db.Column(db.String(40), nullable=True, index=True)
    razorpay_payment_id = db.Column(db.String(40), nullable=True)
    tracking_no = db.Column(db.String(40), nullable=True)
    proof_filename = db.Column(db.String(120), nullable=True)

    flagged = db.Column(db.Boolean, nullable=False, default=False)
    flag_reason = db.Column(db.String(200), nullable=True)

    # "I can't pay" letters: ₹0 order posted when the Letters Fund covers it.
    sponsored_request = db.Column(db.Boolean, nullable=False, default=False)

    # Honest posts-by date, computed from queue depth at admin confirm time.
    promised_date = db.Column(db.Date, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    utr_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)
    posted_at = db.Column(db.DateTime, nullable=True)
    delivered_at = db.Column(db.DateTime, nullable=True)

    template = db.relationship("LetterTemplate")

    @property
    def total(self):
        return self.amount + (self.tip or 0)

    @property
    def is_paid(self):
        return self.status in ("confirmed", "printed", "posted", "delivered")


class LetterTemplate(db.Model):
    __tablename__ = "templates"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(40), unique=True, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    subject_line = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)  # paragraphs separated by blank lines
    active = db.Column(db.Boolean, nullable=False, default=True)


class LedgerEntry(db.Model):
    __tablename__ = "ledger"

    TYPES = ["fee", "tip", "postage", "print", "infra", "refund", "fund"]

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(20), nullable=False)
    # Positive = money in (fee, tip); negative = money out (postage, print,
    # infra, refund). Stored in rupees as float for paise precision (₹41.30).
    amount = db.Column(db.Float, nullable=False)
    note = db.Column(db.String(200), nullable=True)
    order_ref = db.Column(db.String(20), nullable=True)
    receipt_url = db.Column(db.String(300), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class DailyCap(db.Model):
    __tablename__ = "daily_cap"

    date = db.Column(db.Date, primary_key=True)
    cap_limit = db.Column(db.Integer, nullable=False)
    used = db.Column(db.Integer, nullable=False, default=0)


class WaitlistEntry(db.Model):
    __tablename__ = "waitlist"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(254), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)


class Sponsorship(db.Model):
    __tablename__ = "sponsorships"

    id = db.Column(db.Integer, primary_key=True)
    public_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), nullable=False)
    bundle_qty = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending_payment")
    utr = db.Column(db.String(40), nullable=True)
    razorpay_order_id = db.Column(db.String(40), nullable=True, index=True)
    razorpay_payment_id = db.Column(db.String(40), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    utr_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    @property
    def total(self):
        return self.amount
