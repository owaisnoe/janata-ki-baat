import math
import secrets
from datetime import datetime, timedelta, timezone

from flask import current_app

from ..extensions import db
from ..models import DailyCap, Order

IST = timezone(timedelta(hours=5, minutes=30))

# No ambiguous chars (0/O, 1/I/L) — codes get read aloud over the phone.
CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def ist_now():
    return datetime.now(IST)


def ist_today():
    return ist_now().date()


def gen_public_code(prefix="JKB-", model=None):
    from ..models import Order
    model = model or Order
    while True:
        code = prefix + "".join(secrets.choice(CODE_ALPHABET) for _ in range(7))
        if not model.query.filter_by(public_code=code).first():
            return code


def fund_balance():
    from ..models import LedgerEntry
    total = db.session.query(db.func.sum(LedgerEntry.amount)).filter(
        LedgerEntry.type.in_(["fund", "tip"])).scalar()
    return float(total or 0)


def _cap_row(for_date=None):
    d = for_date or ist_today()
    row = db.session.get(DailyCap, d)
    if row is None:
        cap_limit = current_app.config["DAILY_CAP"] or 50
        row = DailyCap(date=d, cap_limit=cap_limit, used=0)
        db.session.add(row)
        db.session.commit()
    return row


def slots_left():
    row = _cap_row()
    return max(0, row.cap_limit - row.used)


def consume_slot():
    """Uncapped when DAILY_CAP<=0 (launch decision, spec §8); the guarded
    UPDATE below is the re-enable path."""
    if current_app.config["DAILY_CAP"] <= 0:
        return True
    row = _cap_row()
    # Guarded UPDATE so two simultaneous orders can't both take the last slot.
    taken = (
        DailyCap.query.filter(
            DailyCap.date == row.date, DailyCap.used < DailyCap.cap_limit
        ).update({DailyCap.used: DailyCap.used + 1})
    )
    db.session.commit()
    return bool(taken)


def promised_post_date():
    """Honest posts-by date: queue depth / operator pace, skipping Sundays."""
    queue = Order.query.filter(
        Order.status.in_(["utr_submitted", "confirmed", "printed"])
    ).count()
    days = max(1, math.ceil((queue + 1) / current_app.config["BATCH_PACE"]))
    d, added = ist_today(), 0
    while added < days:
        d += timedelta(days=1)
        if d.weekday() != 6:  # post offices work Saturdays; Sunday off
            added += 1
    return d


def release_slot(order):
    """Free the slot of an order expired the same IST day it was created."""
    created_ist = order.created_at.replace(tzinfo=timezone.utc).astimezone(IST)
    if created_ist.date() != ist_today():
        return
    DailyCap.query.filter(DailyCap.date == ist_today(), DailyCap.used > 0).update(
        {DailyCap.used: DailyCap.used - 1}
    )
    db.session.commit()


def letters_count():
    """The public counter: confirmed-and-beyond letters only (real letters)."""
    return db.session.query(db.func.count(Order.id)).filter(
        Order.serial_no.isnot(None)
    ).scalar() or 0


def sponsored_letters_count():
    """Total bundle_qty across confirmed sponsorships."""
    from ..models import Sponsorship
    total = db.session.query(db.func.sum(Sponsorship.bundle_qty)).filter(
        Sponsorship.status == "confirmed"
    ).scalar()
    return int(total or 0)


def next_serial():
    top = db.session.query(db.func.max(Order.serial_no)).scalar()
    return (top or 0) + 1
