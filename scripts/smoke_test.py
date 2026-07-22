"""End-to-end smoke test of the full loop against a throwaway SQLite DB.

  ./.venv/Scripts/python scripts/smoke_test.py

Drives: landing -> write -> pay -> UTR -> admin confirm -> print run ->
proof upload -> status/share/PDF -> ledger -> policies -> moderation flag ->
cap-full waitlist redirect. Exits non-zero on first failure.
"""
import io
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TEST_DB = ROOT / "instance" / "smoke_test.db"
TEST_DB.parent.mkdir(exist_ok=True)
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import DailyCap, LedgerEntry, Order  # noqa: E402
from app.services.util import ist_today  # noqa: E402

PASS = 0


def check(label, cond, detail=""):
    global PASS
    if not cond:
        print(f"FAIL: {label} {detail}")
        sys.exit(1)
    PASS += 1
    print(f"  ok: {label}")


def main():
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    # --- public pages render ---
    for path in ["/", "/write", "/ledger", "/diy", "/about", "/privacy",
                 "/content-policy", "/refunds"]:
        r = client.get(path)
        check(f"GET {path}", r.status_code == 200, f"-> {r.status_code}")
    r = client.get("/nonexistent")
    check("404 page", r.status_code == 404 and b"Accountability" in r.data)
    r = client.get("/diy/kit.pdf")
    check("DIY kit PDF", r.status_code == 200 and r.data[:4] == b"%PDF")

    # --- Task 1: Ink & Letterpress chrome ---
    r = client.get("/")
    check("masthead students line", b"FROM THE STUDENTS" in r.data)
    check("no Anton font", b"Anton" not in r.data)
    check("Playfair + Caveat loaded", b"Playfair+Display" in r.data
          and b"Caveat" in r.data)
    css = (ROOT / "app" / "static" / "css" / "style.css").read_text(encoding="utf-8")
    for hexcode in ["3D0808", "6E1010", "C1121F", "A50F1B"]:
        check(f"no maroon {hexcode} in css", hexcode not in css)
    check("tokens present", "--verm-deep" in css and "#F7F3EC" in css)

    # --- Task 2: SVG art macro library ---
    r = client.get("/")
    check("art macros render", b"aria-hidden" in r.data and b"<svg" in r.data)

    # --- Task 3: home page v5 order ---
    r = client.get("/")
    check("hero slogan", b"Mann&nbsp;Ki&nbsp;Baat" in r.data
          and b"Janata&nbsp;Ki&nbsp;Baat" in r.data)
    check("live news desk", b"LIVE" in r.data and b"SOURCED, NOT RUMOURED" in r.data)
    check("no slots scarcity on home", b"slots" not in r.data.lower())
    check("posters on home", b"TAP TO SHARE" in r.data)
    check("sponsor band on home", b"Letters Fund" in r.data)

    # --- write flow ---
    form = {
        "template": "neet-accountability",
        "name": "Asha Test",
        "city": "Tumakuru, Karnataka",
        "email": "asha@example.com",
        "phone": "",
        "personal_para": "I appeared for NEET-UG 2026 and lost a year to "
                         "this leak. Please act.",
        "reply_address": "12 MG Road, Tumakuru 572101",
        "tier": "speedpost",
        "tip": "20",
    }
    r = client.post("/preview", data=form)
    check("live PDF preview", r.status_code == 200 and r.data[:4] == b"%PDF")

    r = client.post("/write", data=form)
    check("order created", r.status_code == 302 and "/pay/JKB-" in r.headers["Location"])
    code = r.headers["Location"].rstrip("/").split("/")[-1]

    with app.app_context():
        order = Order.query.filter_by(public_code=code).first()
        check("order in DB", order is not None and order.total == 79)
        check("uncapped: no slot row consumed",
              db.session.get(DailyCap, ist_today()) is None)
        order_id = order.id

    r = client.get(f"/pay/{code}")
    check("pay page", r.status_code == 200 and b"UPI" in r.data
          and code.encode() in r.data)
    check("stamp-frame QR", b"stamp-frame" in r.data)
    check("share moment on pay", b"Tell one person" in r.data)
    r = client.get(f"/pay/{code}/qr.png")
    check("UPI QR", r.status_code == 200 and r.data[:8] == b"\x89PNG\r\n\x1a\n")

    r = client.post(f"/pay/{code}/utr", data={"utr": "415023998877"})
    check("UTR submit", r.status_code == 302)
    r = client.get(f"/letter/{code}")
    check("status page (utr_submitted)", r.status_code == 200
          and b"UTR received" in r.data)

    # --- admin loop ---
    r = client.post("/admin/login", data={"password": "wrong"})
    check("admin rejects wrong password", b"Wrong password" in r.data)
    r = client.post("/admin/login",
                    data={"password": os.environ.get("ADMIN_PASSWORD",
                                                     "dev-admin-123")})
    check("admin login", r.status_code == 302)
    r = client.get("/admin/")
    check("admin queue", r.status_code == 200 and code.encode() in r.data)

    r = client.post(f"/admin/order/{order_id}/confirm")
    check("confirm payment", r.status_code == 302)
    with app.app_context():
        order = db.session.get(Order, order_id)
        check("serial assigned", order.serial_no == 1)
        check("fee+tip on ledger",
              LedgerEntry.query.filter_by(order_ref=code).count() == 2)

    r = client.post("/admin/print-run")
    check("print run PDF", r.status_code == 200 and r.data[:4] == b"%PDF")
    with app.app_context():
        check("flipped to printed",
              db.session.get(Order, order_id).status == "printed")

    # proof upload (tiny generated PNG)
    from PIL import Image
    img = io.BytesIO()
    Image.new("RGB", (60, 40), "#C1121F").save(img, "PNG")
    img.seek(0)
    r = client.post(f"/admin/order/{order_id}/posted", data={
        "tracking_no": "EK123456789IN",
        "proof": (img, "envelope.png"),
    }, content_type="multipart/form-data")
    check("mark posted", r.status_code == 302)
    with app.app_context():
        order = db.session.get(Order, order_id)
        check("posted with proof", order.status == "posted"
              and order.proof_filename)
        check("postage on ledger", LedgerEntry.query.filter_by(
            order_ref=code, type="postage").count() == 1)

    # --- proof, PDF, cards on public status ---
    r = client.get(f"/letter/{code}")
    check("status shows proof + tracking", b"EK123456789IN" in r.data
          and b"THE PROOF" in r.data)
    check("ownership header", b"letter to the Education Ministry" in r.data)
    check("journey timeline", b"journey" in r.data)
    check("thunk animation hook", b"postmark-thunk" in r.data)
    r = client.get(f"/letter/{code}/proof")
    check("proof photo served", r.status_code == 200)
    r = client.get(f"/letter/{code}/letter.pdf")
    check("letter PDF", r.status_code == 200 and r.data[:4] == b"%PDF")
    for fmt in ["square", "story"]:
        r = client.get(f"/letter/{code}/card.png?fmt={fmt}")
        check(f"share card {fmt}", r.status_code == 200
              and r.data[:8] == b"\x89PNG\r\n\x1a\n")

    r = client.post(f"/admin/order/{order_id}/delivered")
    with app.app_context():
        check("delivered", db.session.get(Order, order_id).status == "delivered")

    # --- ledger totals ---
    r = client.get("/ledger")
    check("ledger shows entries", r.status_code == 200 and code.encode() in r.data)

    # --- moderation flag ---
    form2 = dict(form, email="second@example.com",
                 personal_para="I will burn down the ministry.")
    r = client.post("/write", data=form2)
    check("flagged order accepted", r.status_code == 302)
    code2 = r.headers["Location"].rstrip("/").split("/")[-1]
    with app.app_context():
        o2 = Order.query.filter_by(public_code=code2).first()
        check("moderation flag set", o2.flagged and "burn down" in o2.flag_reason)

    # --- emails landed in dev outbox ---
    outbox = Path(app.instance_path) / "outbox"
    mails = list(outbox.glob("*.html")) if outbox.exists() else []
    check("emails in dev outbox (2 received + 1 confirmed + 1 posted)",
          len(mails) >= 4, f"found {len(mails)}")

    # --- uncapped default + promised date ---
    with app.app_context():
        row = db.session.get(DailyCap, ist_today())
        if row:
            row.used = 10_000
            db.session.commit()
    form3 = dict(form, email="third@example.com", personal_para="")
    r = client.post("/write", data=form3)
    check("uncapped: order accepted past any cap", r.status_code == 302
          and "/pay/JKB-" in r.headers["Location"])
    with app.app_context():
        o = Order.query.filter_by(public_code=code).first()
        check("promised_date set at confirm", o.promised_date is not None)
    r = client.get("/write")
    check("write shows posts-by date", b"posts by" in r.data.lower())

    # --- Task 5: write page seals, tip chips, ink signature, city postmark ---
    r = client.get("/write")
    check("tip chips", b"cutting chai" in r.data and b"full tiffin" in r.data)
    check("ink signature slot", b'data-lp="sig"' in r.data)
    check("city postmark slot", b"city-postmark" in r.data)

    # --- capped mode still works as the emergency brake ---
    app.config["DAILY_CAP"] = 1
    with app.app_context():
        row = db.session.get(DailyCap, ist_today())
        row.cap_limit, row.used = 1, 1
        db.session.commit()
    r = client.post("/write", data=dict(form3, email="fourth@example.com"))
    check("capped: redirects to waitlist", r.status_code == 302
          and "waitlist" in r.headers["Location"])
    r = client.post("/waitlist", data={"email": "fourth@example.com"})
    check("waitlist capture", r.status_code == 302)
    app.config["DAILY_CAP"] = 0

    # --- sponsor flow ---
    r = client.get("/sponsor")
    check("sponsor page", r.status_code == 200 and b"Letters Fund" in r.data)
    r = client.post("/sponsor", data={"email": "daani@example.com", "bundle": "3"})
    check("sponsorship created", r.status_code == 302 and "/sponsor/pay/JKS-" in r.headers["Location"])
    scode = r.headers["Location"].rstrip("/").split("/")[-1]
    r = client.get(f"/sponsor/pay/{scode}")
    check("sponsor pay page", r.status_code == 200 and b"177" in r.data)
    r = client.post(f"/sponsor/pay/{scode}/utr", data={"utr": "555023998877"})
    check("sponsor UTR", r.status_code == 302)
    with app.app_context():
        from app.models import Sponsorship
        s = Sponsorship.query.filter_by(public_code=scode).first()
        sid = s.id
    r = client.post(f"/admin/sponsor/{sid}/confirm")
    check("sponsor confirmed", r.status_code == 302)
    with app.app_context():
        check("fund entry on ledger", LedgerEntry.query.filter_by(
            type="fund", order_ref=scode).count() == 1)

    # --- can't-pay sponsored request ---
    form_sp = dict(form, email="hostel@example.com", personal_para="",
                   cant_pay="on")
    r = client.post("/write", data=form_sp)
    check("sponsored request accepted", r.status_code == 302
          and "/letter/JKB-" in r.headers["Location"])
    code_sp = r.headers["Location"].rstrip("/").split("/")[-1]
    with app.app_context():
        osp = Order.query.filter_by(public_code=code_sp).first()
        check("sponsored request flags", osp.sponsored_request
              and osp.amount == 0 and osp.status == "utr_submitted")
        osp_id = osp.id
    r = client.get("/admin/?tab=confirm")
    check("FUND tag + fund balance in queue", b"FUND" in r.data
          and b"fund \xe2\x82\xb9" in r.data)
    r = client.post(f"/admin/order/{osp_id}/confirm")
    with app.app_context():
        check("fund debited for sponsored letter", LedgerEntry.query.filter_by(
            type="fund", order_ref=code_sp).filter(LedgerEntry.amount < 0).count() == 1)

    print(f"\nALL {PASS} CHECKS PASSED")


if __name__ == "__main__":
    main()
