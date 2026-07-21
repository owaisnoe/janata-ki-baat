"""cPanel cron (plan §8): expire unpaid orders after 24 h and free their
daily-cap slots. Run hourly:

  0 * * * * cd ~/janata-ki-baat && ./venv/bin/python scripts/expire_orders.py
"""
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Order, utcnow  # noqa: E402
from app.services.util import release_slot  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        cutoff = utcnow() - timedelta(hours=24)
        stale = Order.query.filter(
            Order.status == "pending_payment", Order.created_at < cutoff
        ).all()
        for order in stale:
            order.status = "expired"
            release_slot(order)
        db.session.commit()
        print(f"expired {len(stale)} unpaid orders")


if __name__ == "__main__":
    main()
