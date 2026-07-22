# Janata Ki Baat — The People's Post

> He talks. The people write back. We print, post & prove your letter to the
> Education Ministry — you pay what the stamp costs.

Flask + Jinja server-rendered app (plan.md §8). SQLite locally, MySQL on
cPanel, deployable via cPanel *Setup Python App* (Passenger). Fully portable
to any VPS/PaaS in under an hour — nothing here is cPanel-specific.

## Local development (Windows / Git Bash)

```bash
python -m venv .venv
./.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env        # then edit: SECRET_KEY, ADMIN_PASSWORD, UPI_VPA
./.venv/Scripts/python run.py
# → http://127.0.0.1:5000        (admin at /admin, DB auto-created + seeded)
```

Dev conveniences: no SMTP configured → emails are written to
`instance/outbox/*.html`; no Turnstile keys → the check is skipped.

**Cap & pace env vars:**
- `DAILY_CAP` — max letters accepted per day. `0` (default, the launch
  decision) means **uncapped**; any positive integer re-enables the brake
  and starts routing overflow to the waitlist once hit.
- `BATCH_PACE` — letters the operator can realistically post per working
  day (default `50`). Drives the honest "posts by …" date shown at write
  time and on confirm (`promised_post_date()` — queue depth ÷ pace,
  skipping Sundays).

**Batch-photo drop folder:** drop envelope-batch JPEGs into
`app/static/batches/*.jpg` (create the folder — it's gitignored) and
they'll show up on the home page proof wall automatically, newest first.
No DB entry or restart needed.

## The full loop (dogfood before launch — plan §12 H30–36)

1. `/write` → pick letter, fill details, **Post my letter →**
2. `/pay/JKB-…` → scan QR (your own VPA), submit any UTR
3. `/admin` → *Confirm UTR* tab → **Confirm ✓** (assigns Letter #, fee+tip
   hit the ledger, confirmation email fires)
4. *To print* tab → **Print run** (downloads merged letters+labels PDF,
   flips orders to `printed`)
5. Order page → upload envelope photo + tracking no. → **Mark posted**
   (proof email fires, postage hits the ledger)
6. `/letter/JKB-…` → timeline, proof photo, PDF, share cards, captions

## cPanel deployment (Namecheap Stellar Business)

1. **Domain & DNS:** buy janatakibaat.in → nameservers to Cloudflare (free)
   → proxy on, AutoSSL in cPanel. Add Turnstile site → keys into `.env`.
2. **MySQL:** cPanel → MySQL Databases → create DB + user, note the prefixed
   names → `DATABASE_URL=mysql+pymysql://user:pass@localhost/dbname`.
3. **App:** cPanel → *Setup Python App* → Python 3.x, app root
   `janata-ki-baat`, startup file `passenger_wsgi.py`, entry `application`.
   Upload the repo (git clone or zip), then in the app's venv:
   `pip install -r requirements.txt`. Restart. Tables auto-create on boot.
4. **Mail:** create `letters@janatakibaat.in` mailbox → SMTP creds into
   `.env`. Set SPF + DKIM in cPanel Email Deliverability, then score ≥9 on
   mail-tester.com **before** launch.
5. **Cron** (cPanel → Cron Jobs):
   - hourly — `expire_orders.py` (24 h unpaid expiry, frees slots)
   - daily — `purge_addresses.py` (DPDP: reply addresses purged 30 d
     post-delivery)
   - daily — `sla_check.py` (lists orders due automatic refund)
   - nightly — `backup.sh` with `DB_NAME` env set (pull off-server weekly)
6. **Config hygiene:** real `SECRET_KEY` (`python -c "import secrets;
   print(secrets.token_hex(32))"`), strong `ADMIN_PASSWORD`, `BASE_URL=https://janatakibaat.in`,
   operator identity vars filled (they render on /about).

## Launch checklist (plan §12)

- [ ] HTTPS live on janatakibaat.in (Cloudflare + AutoSSL)
- [ ] ₹1 test order end-to-end (write → pay → confirm → print → post → proof)
- [ ] Refund path tested (admin Refund + manual UPI send + ledger entry)
- [ ] Cap + waitlist tested (set DAILY_CAP=1 temporarily, fill it)
- [ ] Disclaimer visible on every page (base template footer — verify)
- [ ] mail-tester ≥9 for all three emails
- [ ] Mobile + contrast pass
- [ ] Poster share test on a real Android phone (Web Share API + saved PNG)
- [ ] Thunk animation + signature check on mobile Safari/Chrome
- [ ] Cloudflare Web Analytics token in `.env`
- [ ] DB + repo backed up
- [ ] Razorpay individual KYC filed (swap-in is Phase 2)

## Repo map

```
app/
  __init__.py        app factory; DB auto-create + template seed
  config.py          all env config; tiers & pricing; ministry address
  models.py          orders / templates / ledger / daily_cap / waitlist
  letter_templates.py  the 3 formal letters (T1/T2/T3)
  moderation.py      keyword auto-flag for personal paragraphs
  routes/public.py   landing, write, pay, status, ledger, diy, policies,
                     sponsor + sponsor pay
  routes/admin.py    ops queue: confirm → print run → post+proof → delivered
  services/          pdf (reportlab), sharecard (Pillow), posters (Pillow —
                     shareable letter-posted poster PNGs), mailer (SMTP),
                     payments (UPI QR/intent + Turnstile), util (codes/caps)
  templates/         _art.html (SVG art macros: stamp, postmark, letterhead
                     doodles), sponsor.html / sponsor_pay.html,
                     emails/sponsor_receipt.html
  static/            fonts/ (bundled Playfair Display + Caveat, OFL — no
                     external font requests), batches/ (operator-dropped
                     proof-wall JPEGs, gitignored), zine-brutalist UI
                     (plan §7 tokens)
scripts/             cron: expiry, DPDP purge, SLA watchdog, backup
passenger_wsgi.py    cPanel entry · run.py local entry
```

**Standing rules:** microcopy can joke, letters never do. Fees ≠ donations.
The cap is sacred. The ops is the content.
