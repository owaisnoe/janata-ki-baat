import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")
    BASE_URL = os.environ.get("BASE_URL", "http://127.0.0.1:5000").rstrip("/")

    SQLALCHEMY_DATABASE_URI = (
        os.environ.get("DATABASE_URL")
        or f"sqlite:///{(BASE_DIR / 'instance' / 'jkb.db').as_posix()}"
    )
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

    UPI_VPA = os.environ.get("UPI_VPA", "")
    UPI_PAYEE_NAME = os.environ.get("UPI_PAYEE_NAME", "Janata Ki Baat")

    DAILY_CAP = int(os.environ.get("DAILY_CAP", "0"))  # 0 = uncapped
    BATCH_PACE = int(os.environ.get("BATCH_PACE", "50"))

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASS = os.environ.get("SMTP_PASS", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "Janata Ki Baat <letters@janatakibaat.in>")

    TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "")
    TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")

    CF_ANALYTICS_TOKEN = os.environ.get("CF_ANALYTICS_TOKEN", "")

    # Named operator identity was removed (student-collective framing on
    # /about). Only a working grievance/contact address is exposed — required
    # by the IT Rules and used across /about, /privacy, /refunds, footer, pay.
    OPERATOR_CONTACT = os.environ.get("OPERATOR_CONTACT", "letters@janatakibaat.in")

    # Proof photos live OUTSIDE the web root; served only via code-gated routes.
    UPLOAD_DIR = BASE_DIR / "uploads" / "proofs"
    CARD_CACHE_DIR = BASE_DIR / "app" / "static" / "cards"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB upload ceiling

    # Tiers (plan §5). Amounts in whole rupees; breakdowns shown publicly.
    TIERS = {
        "speedpost": {
            "label": "Speed Post",
            "price": 59,
            "postage_cost": 41.30,
            "print_cost": 5.00,
            "breakdown": "₹41.30 postage + ~₹5 print & envelope + ~₹13 ops buffer",
            "promise": "Physical letter, envelope photo at the post office, "
                       "India Post tracking number, delivery-status link.",
        },
        "epost": {
            "label": "ePost",
            "price": 19,
            "postage_cost": 10.00,
            "print_cost": 0.00,
            "breakdown": "₹10/page India Post ePost + ₹9 buffer",
            "promise": "India Post prints & delivers; submission receipt "
                       "screenshot as proof.",
        },
    }
    TIP_MAX = 500

    SPONSOR_BUNDLES = [(1, 59), (3, 177), (5, 295), (10, 590)]

    # SLA (plan §9)
    SLA_POST_DAYS = 2
    SLA_REFUND_DAYS = 5

    MINISTRY_ADDRESS = (
        "The Union Minister of Education\n"
        "Ministry of Education, Government of India\n"
        "Shastri Bhawan, Dr. Rajendra Prasad Road\n"
        "New Delhi – 110001"
    )
