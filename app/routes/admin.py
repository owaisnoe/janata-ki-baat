import csv
import io
import secrets
from functools import wraps
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
    session,
    url_for,
)

from ..extensions import db, limiter
from ..models import LedgerEntry, Order, Sponsorship, WaitlistEntry, utcnow
from ..responses import send_inline_bytes
from ..services import mailer, pdf
from ..services.util import fund_balance, next_serial, release_slot

bp = Blueprint("admin", __name__)

ALLOWED_PROOF_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin"):
            return redirect(url_for("admin.login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def login():
    if request.method == "POST":
        configured = current_app.config["ADMIN_PASSWORD"]
        supplied = request.form.get("password", "")
        if configured and secrets.compare_digest(supplied, configured):
            session["admin"] = True
            session.permanent = False
            return redirect(request.args.get("next") or url_for("admin.queue"))
        flash("Wrong password.", "error")
    return render_template("admin/login.html")


@bp.get("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("public.index"))


@bp.get("/")
@admin_required
def queue():
    tab = request.args.get("tab", "confirm")
    tab_queries = {
        "confirm": Order.query.filter_by(status="utr_submitted")
        .order_by(Order.utr_at),
        "print": Order.query.filter_by(status="confirmed")
        .order_by(Order.confirmed_at),
        "post": Order.query.filter_by(status="printed")
        .order_by(Order.confirmed_at),
        "posted": Order.query.filter_by(status="posted")
        .order_by(Order.posted_at.desc()),
        "pending": Order.query.filter_by(status="pending_payment")
        .order_by(Order.created_at.desc()),
        "done": Order.query.filter(Order.status.in_(["delivered", "expired",
                                                     "refunded"]))
        .order_by(Order.created_at.desc()),
        "sponsor": Sponsorship.query.filter_by(status="utr_submitted")
        .order_by(Sponsorship.utr_at),
    }
    if tab not in tab_queries:
        tab = "confirm"
    sponsorships = None
    if tab == "sponsor":
        sponsorships = tab_queries["sponsor"].limit(200).all()
        orders = []
    else:
        orders = tab_queries[tab].limit(200).all()
    counts = {name: q.count() for name, q in tab_queries.items()}
    flagged_count = Order.query.filter_by(flagged=True).filter(
        Order.status.in_(["utr_submitted", "confirmed"])
    ).count()
    waitlist_count = WaitlistEntry.query.count()
    return render_template(
        "admin/queue.html", orders=orders, tab=tab, counts=counts,
        flagged_count=flagged_count, waitlist_count=waitlist_count,
        sponsorships=sponsorships, fund=fund_balance(),
    )


def _order_or_404(order_id):
    order = db.session.get(Order, order_id)
    if order is None:
        abort(404)
    return order


@bp.get("/order/<int:order_id>")
@admin_required
def order_detail(order_id):
    return render_template("admin/order.html", order=_order_or_404(order_id))


@bp.post("/order/<int:order_id>/confirm")
@admin_required
def confirm(order_id):
    order = _order_or_404(order_id)
    if order.status != "utr_submitted":
        flash("Order is not awaiting confirmation.", "error")
        return redirect(url_for("admin.queue"))
    from ..services.orders import confirm_order
    confirm_order(order)
    flash(f"{order.public_code} confirmed as Letter #{order.serial_no}.",
          "success")
    return redirect(url_for("admin.queue"))


@bp.post("/sponsor/<int:s_id>/confirm")
@admin_required
def sponsor_confirm(s_id):
    s = db.session.get(Sponsorship, s_id)
    if s is None or s.status != "utr_submitted":
        flash("Sponsorship not awaiting confirmation.", "error")
        return redirect(url_for("admin.queue", tab="sponsor"))
    from ..services.orders import confirm_sponsorship
    confirm_sponsorship(s)
    flash(f"{s.public_code} confirmed — ₹{s.amount} into the Letters Fund.", "success")
    return redirect(url_for("admin.queue", tab="sponsor"))


@bp.post("/order/<int:order_id>/expire")
@admin_required
def expire(order_id):
    order = _order_or_404(order_id)
    if order.is_paid:
        flash("Paid orders can't be expired — refund instead.", "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))
    order.status = "expired"
    release_slot(order)
    db.session.commit()
    flash(f"{order.public_code} expired.", "success")
    return redirect(url_for("admin.queue"))


@bp.post("/order/<int:order_id>/refund")
@admin_required
def refund(order_id):
    order = _order_or_404(order_id)
    order.status = "refunded"
    db.session.add(LedgerEntry(type="refund", amount=-order.total,
                               order_ref=order.public_code,
                               note="refund via same UPI rail"))
    db.session.commit()
    flash(f"{order.public_code} marked refunded — now actually send ₹"
          f"{order.total} back on UPI.", "success")
    return redirect(url_for("admin.queue"))


@bp.post("/order/<int:order_id>/drop-para")
@admin_required
def drop_para(order_id):
    order = _order_or_404(order_id)
    order.personal_para = None
    order.flagged = False
    order.flag_reason = None
    db.session.commit()
    flash("Personal paragraph dropped; template letter will be sent.",
          "success")
    return redirect(url_for("admin.order_detail", order_id=order.id))


@bp.post("/print-run")
@admin_required
def print_run():
    orders = Order.query.filter_by(status="confirmed").order_by(
        Order.serial_no).all()
    if not orders:
        flash("Nothing confirmed to print.", "error")
        return redirect(url_for("admin.queue", tab="print"))
    buf = pdf.print_run_pdf(orders)
    for order in orders:
        order.status = "printed"
    db.session.commit()
    stamp = utcnow().strftime("%Y%m%d-%H%M")
    return send_inline_bytes(
        buf, "application/pdf", as_attachment=True,
        download_name=f"print-run-{stamp}-{len(orders)}-letters.pdf")


@bp.post("/order/<int:order_id>/posted")
@admin_required
def mark_posted(order_id):
    order = _order_or_404(order_id)
    if order.status not in ("printed", "confirmed"):
        flash("Order must be printed (or at least confirmed) first.", "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))

    tracking = (request.form.get("tracking_no") or "").strip()[:40]
    photo = request.files.get("proof")
    if order.tier == "speedpost" and not tracking:
        flash("Speed Post needs the consignment/tracking number.", "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))
    if photo and photo.filename:
        ext = Path(photo.filename).suffix.lower()
        if ext not in ALLOWED_PROOF_EXT:
            flash(f"Proof must be one of: {', '.join(sorted(ALLOWED_PROOF_EXT))}",
                  "error")
            return redirect(url_for("admin.order_detail", order_id=order.id))
        fname = f"{order.public_code}{ext}"
        photo.save(current_app.config["UPLOAD_DIR"] / fname)
        order.proof_filename = fname
    elif not order.proof_filename:
        flash("Upload the envelope/receipt photo — proof is the product.",
              "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))

    order.tracking_no = tracking or None
    order.status = "posted"
    order.posted_at = utcnow()
    tier = current_app.config["TIERS"][order.tier]
    cost = tier["postage_cost"] + tier["print_cost"]
    db.session.add(LedgerEntry(type="postage", amount=-cost,
                               order_ref=order.public_code,
                               note=f"{tier['label']} postage + print"))
    db.session.commit()

    status_url = current_app.config["BASE_URL"] + url_for(
        "public.status", code=order.public_code)
    mailer.send_email(
        order.email,
        f"Posted. Letter #{order.serial_no:,} is in the mail — here's proof",
        render_template("emails/posted.html", order=order,
                        status_url=status_url),
    )
    flash(f"{order.public_code} posted — proof email sent.", "success")
    return redirect(url_for("admin.queue", tab="post"))


@bp.post("/order/<int:order_id>/delivered")
@admin_required
def mark_delivered(order_id):
    order = _order_or_404(order_id)
    if order.status != "posted":
        flash("Only posted orders can be delivered.", "error")
        return redirect(url_for("admin.order_detail", order_id=order.id))
    order.status = "delivered"
    order.delivered_at = utcnow()
    db.session.commit()
    flash(f"{order.public_code} delivered.", "success")
    return redirect(url_for("admin.queue", tab="posted"))


@bp.post("/ledger")
@admin_required
def add_ledger():
    try:
        amount = float(request.form.get("amount", ""))
    except ValueError:
        flash("Amount must be a number (negative = money out).", "error")
        return redirect(url_for("admin.queue"))
    entry_type = request.form.get("type", "infra")
    if entry_type not in LedgerEntry.TYPES:
        entry_type = "infra"
    db.session.add(LedgerEntry(
        type=entry_type, amount=amount,
        note=(request.form.get("note") or "").strip()[:200] or None,
        receipt_url=(request.form.get("receipt_url") or "").strip()[:300] or None,
    ))
    db.session.commit()
    flash("Ledger entry added.", "success")
    return redirect(url_for("public.ledger"))


@bp.get("/export.csv")
@admin_required
def export_csv():
    buf = io.StringIO()
    writer = csv.writer(buf)
    cols = ["public_code", "serial_no", "status", "tier", "amount", "tip",
            "name", "city", "email", "phone", "utr", "tracking_no",
            "flagged", "created_at", "confirmed_at", "posted_at",
            "delivered_at"]
    writer.writerow(cols)
    for o in Order.query.order_by(Order.id).all():
        writer.writerow([getattr(o, c) for c in cols])
    out = io.BytesIO(buf.getvalue().encode("utf-8"))
    return send_inline_bytes(out, "text/csv", as_attachment=True,
                             download_name="jkb-orders.csv")
