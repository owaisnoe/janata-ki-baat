"""DPDP hygiene (plan §11): purge optional reply addresses 30 days after
delivery. Run daily:

  30 2 * * * cd ~/janata-ki-baat && ./venv/bin/python scripts/purge_addresses.py
"""
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Order, utcnow  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        cutoff = utcnow() - timedelta(days=30)
        purged = Order.query.filter(
            Order.reply_address.isnot(None),
            Order.delivered_at.isnot(None),
            Order.delivered_at < cutoff,
        ).update({Order.reply_address: None})
        db.session.commit()
        print(f"purged {purged} reply addresses")


if __name__ == "__main__":
    main()
