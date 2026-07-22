import json
import re
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from ..extensions import db, limiter
from ..models import LedgerEntry, LetterTemplate, Order, WaitlistEntry
from ..moderation import PERSONAL_PARA_MAX, check_personal_para
from ..services import mailer, payments, pdf, sharecard
from ..services.util import consume_slot, gen_public_code, ist_now, promised_post_date

bp = Blueprint("public", __name__)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
UTR_RE = re.compile(r"^[A-Za-z0-9]{6,22}$")

SHARE_CAPTIONS = [
    "I couldn't make it to Jantar Mantar. My letter could. ✉️ #JanataKiBaat",
    "Mann Ki Baat sunn li. Janata Ki Baat bhej di. 📮 janatakibaat.in",
    "Letter {n} to the Education Ministry is in the mail. Your move.",
]


def _fuel():
    """Today's fuel strip (plan §4): hand-curated, sourced headlines."""
    path = Path(current_app.root_path) / "data" / "fuel.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"updated_at": "", "items": []}


def _posters():
    path = Path(current_app.root_path) / "data" / "posters.json"
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    from ..services.util import letters_count
    n = letters_count()
    out = []
    for p in raw:
        q = dict(p)
        for k in ("headline", "hand_line", "caption"):
            q[k] = q[k].replace("{count}", f"{n:,}").replace("{next}", f"{n + 1:,}")
        out.append(q)
    return out


def _get_order(code):
    order = Order.query.filter_by(public_code=code.upper()).first()
    if order is None:
        abort(404)
    return order


@bp.get("/")
def index():
    batches_dir = Path(current_app.static_folder) / "batches"
    batch_shots = sorted(batches_dir.glob("*.jpg")) if batches_dir.exists() else []
    return render_template(
        "index.html", fuel=_fuel(), posters=_posters(),
        batch_shots=batch_shots, now=ist_now(),
    )


def _render_write(templates, picked, values, errors, status_code=200):
    tpl_json = json.dumps({
        t.slug: {
            "subject": t.subject_line,
            "paras": [p.strip() for p in t.body.split("\n\n") if p.strip()],
        }
        for t in templates
    })
    return render_template(
        "write.html", templates=templates, picked=picked,
        values=values, errors=errors, para_max=PERSONAL_PARA_MAX,
        tpl_json=tpl_json, today_str=ist_now().strftime("%d %B %Y"),
        eta=promised_post_date(),
    ), status_code


@bp.get("/write")
def write():
    templates = LetterTemplate.query.filter_by(active=True).all()
    picked = request.args.get("t") or (templates[0].slug if templates else None)
    return _render_write(templates, picked, values={}, errors={})


def _validate_write_form(form):
    values = {
        "name": (form.get("name") or "").strip()[:120],
        "city": (form.get("city") or "").strip()[:120],
        "email": (form.get("email") or "").strip()[:254],
        "phone": (form.get("phone") or "").strip()[:20],
        "template": (form.get("template") or "").strip(),
        "personal_para": (form.get("personal_para") or "").strip(),
        "reply_address": (form.get("reply_address") or "").strip()[:300],
        "tier": (form.get("tier") or "speedpost").strip(),
        "tip": form.get("tip", "0"),
    }
    errors = {}
    if len(values["name"]) < 2:
        errors["name"] = "Your full name goes on the letter — we need it."
    if len(values["city"]) < 2:
        errors["city"] = "Your city goes under your signature."
    if not EMAIL_RE.match(values["email"]):
        errors["email"] = "A working email — it's how you get your proof."
    tpl = LetterTemplate.query.filter_by(slug=values["template"], active=True).first()
    if tpl is None:
        errors["template"] = "Pick one of the letters."
    if values["tier"] not in current_app.config["TIERS"]:
        errors["tier"] = "Pick a tier."
    try:
        tip = max(0, min(int(values["tip"] or 0), current_app.config["TIP_MAX"]))
    except ValueError:
        tip = 0
    values["tip"] = tip
    ok, flagged, reason = check_personal_para(values["personal_para"])
    if not ok:
        errors["personal_para"] = reason
    return values, errors, tpl, flagged, reason


@bp.post("/write")
@limiter.limit("8 per hour")
def write_submit():
    if not payments.verify_turnstile(
        request.form.get("cf-turnstile-response"), request.remote_addr
    ):
        flash("The anti-bot check didn't pass. Please try again.", "error")
        return redirect(url_for("public.write"))

    values, errors, tpl, flagged, flag_reason = _validate_write_form(request.form)
    if errors:
        templates = LetterTemplate.query.filter_by(active=True).all()
        return _render_write(templates, values["template"], values, errors,
                             status_code=400)

    if not consume_slot():
        return redirect(url_for("public.index", _anchor="waitlist"))

    tier = current_app.config["TIERS"][values["tier"]]
    order = Order(
        public_code=gen_public_code(),
        name=values["name"],
        city=values["city"],
        email=values["email"],
        phone=values["phone"] or None,
        template_id=tpl.id,
        personal_para=values["personal_para"] or None,
        reply_address=values["reply_address"] or None,
        tier=values["tier"],
        amount=tier["price"],
        tip=values["tip"],
        flagged=flagged,
        flag_reason=flag_reason,
    )
    db.session.add(order)
    db.session.commit()

    pay_url = current_app.config["BASE_URL"] + url_for("public.pay", code=order.public_code)
    mailer.send_email(
        order.email,
        f"Your letter is queued — {order.public_code}",
        render_template("emails/order_received.html", order=order, pay_url=pay_url),
    )
    return redirect(url_for("public.pay", code=order.public_code))


@bp.post("/preview")
@limiter.limit("30 per hour")
def preview_pdf():
    values, _, tpl, _, _ = _validate_write_form(request.form)
    if tpl is None:
        abort(400)
    buf = pdf.letter_pdf(
        tpl,
        values["name"] or "Your Name",
        values["city"] or "Your City",
        values["personal_para"],
        values["reply_address"],
    )
    return send_file(buf, mimetype="application/pdf", download_name="letter-preview.pdf")


@bp.get("/pay/<code>")
def pay(code):
    order = _get_order(code)
    if order.is_paid:
        return redirect(url_for("public.status", code=order.public_code))
    if order.status in ("expired", "refunded"):
        return redirect(url_for("public.status", code=order.public_code))
    return render_template(
        "pay.html", order=order, upi_uri=payments.upi_uri(order),
        poster=(_posters() or [None])[0],
    )


@bp.get("/pay/<code>/qr.png")
def pay_qr(code):
    order = _get_order(code)
    return send_file(payments.qr_png(order), mimetype="image/png")


@bp.post("/pay/<code>/utr")
@limiter.limit("20 per hour")
def pay_utr(code):
    order = _get_order(code)
    if order.status not in ("pending_payment", "utr_submitted"):
        return redirect(url_for("public.status", code=order.public_code))
    utr = (request.form.get("utr") or "").strip().replace(" ", "")
    if not UTR_RE.match(utr):
        flash("That doesn't look like a UPI reference number (UTR). "
              "It's 12 digits in most UPI apps.", "error")
        return redirect(url_for("public.pay", code=order.public_code))
    from ..models import utcnow

    order.utr = utr
    order.status = "utr_submitted"
    order.utr_at = utcnow()
    db.session.commit()
    flash("Got it. We'll match your payment and confirm within a few hours.",
          "success")
    return redirect(url_for("public.status", code=order.public_code))


@bp.get("/letter/<code>")
def status(code):
    order = _get_order(code)
    captions = [c.format(n=f"#{order.serial_no:,}" if order.serial_no else "")
                for c in SHARE_CAPTIONS]
    return render_template("status.html", order=order, captions=captions)


@bp.get("/letter/<code>/letter.pdf")
def letter_pdf_route(code):
    order = _get_order(code)
    buf = pdf.letter_pdf(order.template, order.name, order.city,
                         order.personal_para, order.reply_address)
    return send_file(buf, mimetype="application/pdf",
                     download_name=f"{order.public_code}-letter.pdf")


@bp.get("/letter/<code>/card.png")
def share_card(code):
    order = _get_order(code)
    fmt = "story" if request.args.get("fmt") == "story" else "square"
    path = sharecard.render_card(order, fmt)
    return send_file(path, mimetype="image/png",
                     download_name=f"{order.public_code}-{fmt}.png")


@bp.get("/letter/<code>/proof")
def proof_photo(code):
    order = _get_order(code)
    if not order.proof_filename:
        abort(404)
    return send_file(current_app.config["UPLOAD_DIR"] / order.proof_filename)


@bp.get("/ledger")
def ledger():
    entries = LedgerEntry.query.order_by(LedgerEntry.created_at.desc()).limit(500).all()
    totals = dict(
        db.session.query(LedgerEntry.type, db.func.sum(LedgerEntry.amount))
        .group_by(LedgerEntry.type).all()
    )
    balance = sum(totals.values()) if totals else 0
    return render_template("ledger.html", entries=entries, totals=totals,
                           balance=balance)


@bp.get("/diy")
def diy():
    return render_template("diy.html")


@bp.get("/diy/kit.pdf")
def diy_kit():
    templates = LetterTemplate.query.filter_by(active=True).all()
    return send_file(pdf.diy_kit_pdf(templates), mimetype="application/pdf",
                     download_name="janata-ki-baat-diy-kit.pdf")


@bp.post("/waitlist")
@limiter.limit("10 per hour")
def waitlist():
    email = (request.form.get("email") or "").strip()[:254]
    if not EMAIL_RE.match(email):
        flash("That email didn't look right.", "error")
        return redirect(url_for("public.index", _anchor="waitlist"))
    if not WaitlistEntry.query.filter_by(email=email).first():
        db.session.add(WaitlistEntry(email=email))
        db.session.commit()
    flash("You're on the list — we'll email you when tomorrow's mailbag opens.",
          "success")
    return redirect(url_for("public.index", _anchor="waitlist"))


@bp.get("/about")
def about():
    return render_template("pages/about.html")


@bp.get("/privacy")
def privacy():
    return render_template("pages/privacy.html")


@bp.get("/content-policy")
def content_policy():
    return render_template("pages/content_policy.html")


@bp.get("/refunds")
def refunds():
    return render_template("pages/refunds.html")


@bp.get("/sponsor")
def sponsor():
    from ..models import Sponsorship
    from ..services.util import fund_balance
    sponsored = Sponsorship.query.filter_by(status="confirmed").with_entities(
        db.func.sum(Sponsorship.bundle_qty)).scalar() or 0
    return render_template("sponsor.html", bundles=current_app.config["SPONSOR_BUNDLES"],
                           fund=fund_balance(), sponsored=sponsored)


@bp.post("/sponsor")
@limiter.limit("8 per hour")
def sponsor_create():
    from ..models import Sponsorship
    email = (request.form.get("email") or "").strip()[:254]
    if not EMAIL_RE.match(email):
        flash("A working email, please — that's where your receipt goes.", "error")
        return redirect(url_for("public.sponsor"))
    bundles = dict(current_app.config["SPONSOR_BUNDLES"])
    try:
        qty = int(request.form.get("bundle", "1"))
    except ValueError:
        qty = 1
    if qty not in bundles:
        qty = 1
    s = Sponsorship(public_code=gen_public_code("JKS-", Sponsorship),
                    email=email, bundle_qty=qty, amount=bundles[qty])
    db.session.add(s)
    db.session.commit()
    return redirect(url_for("public.sponsor_pay", code=s.public_code))


def _get_sponsorship(code):
    from ..models import Sponsorship
    s = Sponsorship.query.filter_by(public_code=code.upper()).first()
    if s is None:
        abort(404)
    return s


@bp.get("/sponsor/pay/<code>")
def sponsor_pay(code):
    s = _get_sponsorship(code)
    return render_template("sponsor_pay.html", s=s, upi_uri=payments.upi_uri(s))


@bp.get("/sponsor/pay/<code>/qr.png")
def sponsor_qr(code):
    return send_file(payments.qr_png(_get_sponsorship(code)), mimetype="image/png")


@bp.post("/sponsor/pay/<code>/utr")
@limiter.limit("20 per hour")
def sponsor_utr(code):
    from ..models import utcnow
    s = _get_sponsorship(code)
    utr = (request.form.get("utr") or "").strip().replace(" ", "")
    if not UTR_RE.match(utr):
        flash("That doesn't look like a UPI reference number (UTR).", "error")
        return redirect(url_for("public.sponsor_pay", code=s.public_code))
    s.utr, s.status, s.utr_at = utr, "utr_submitted", utcnow()
    db.session.commit()
    flash("Got it — we'll match your payment and email your receipt.", "success")
    return redirect(url_for("public.sponsor"))
