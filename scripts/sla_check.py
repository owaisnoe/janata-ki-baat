"""SLA watchdog (plan §9): list paid orders posted more than 2 working days
past their promised post-date — these are due an automatic full refund. Prints
them; the refund itself is a manual UPI action + the admin Refund button. Run
daily:

  0 8 * * * cd ~/janata-ki-baat && ./venv/bin/python scripts/sla_check.py
"""
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app  # noqa: E402
from app.models import Order, utcnow  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        overdue = [
            o for o in Order.query.filter(
                Order.status.in_(["confirmed", "printed"])).all()
            if o.promised_date
            and utcnow().date() > o.promised_date + timedelta(days=2)
        ]
        if not overdue:
            print("SLA clean — nothing overdue")
            return
        print(f"SLA BLOWN on {len(overdue)} orders — refund these today:")
        for o in overdue:
            print(f"  {o.public_code}  ₹{o.total}  {o.name} <{o.email}>  "
                  f"promised {o.promised_date:%d %b}")


if __name__ == "__main__":
    main()
