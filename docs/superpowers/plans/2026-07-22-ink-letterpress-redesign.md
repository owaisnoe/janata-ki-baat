# Ink & Letterpress Front-End Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the maroon zine-brutalist front end of the Janata Ki Baat Flask app with the approved "Ink & Letterpress" identity, and add four features: spread-the-word posters, a Sponsor-a-Letter flow, tip chips, and uncapped intake with an honest promised-post-date.

**Architecture:** Server-rendered Flask + Jinja app (blueprints `public`/`admin`), single stylesheet `app/static/css/style.css`, vanilla JS in `app/static/js/main.js`, SQLAlchemy models, services layer (`pdf`, `sharecard`, `mailer`, `payments`, `util`). The redesign is a restyle-in-place: swap the token layer, rebuild templates section-by-section, add two small models. **Visual source of truth:** `docs/superpowers/specs/assets/2026-07-22-homepage-mockup-v5.html` — a complete standalone HTML file whose `<style>` block and body sections are ported nearly verbatim; open it in a browser whenever unsure what something should look like. Spec: `docs/superpowers/specs/2026-07-22-frontend-redesign-design.md`.

**Tech Stack:** Python 3.14 (venv at `.venv`), Flask, Flask-SQLAlchemy, SQLite (dev, file `instance/jkb.db` — disposable), reportlab, Pillow, qrcode. No JS frameworks, no build step, no new pip dependencies.

**Verification model:** This repo has no pytest. The test harness is `scripts/smoke_test.py` — a linear script that drives the app through Flask's test client against a throwaway DB (`instance/smoke_test.db`) and exits non-zero on first failure. Every task follows: add smoke check(s) → run (must FAIL) → implement → run (must PASS) → commit. Run command (Windows Git Bash, from repo root):

```bash
./.venv/Scripts/python scripts/smoke_test.py
```

## Global Constraints

- Tokens (exact values, spec §3): paper `#F7F3EC`, paper-deep `#EFE7D8`, card `#FBF8F2`, ink `#171512`, ink-soft `#2A2622`, verm `#E2401B`, verm-deep `#B93511`, stone `#6E675C`, hair `rgba(23,21,18,.18)`, saffron `#E07C1F`, green `#2E7D32`.
- **No maroon anywhere.** After the final task, `grep -rniE "3D0808|6E1010|C1121F|A50F1B" app/` must return nothing.
- Vermilion `#E2401B` only for text ≥24px or decorative strokes; `#B93511` for small text; body text `#2A2622`.
- Exactly four font families: Playfair Display, Inter, IBM Plex Mono, Caveat. Anton is removed. Caveat only for "human ink" (addresses, signatures, hand annotations) — never UI chrome.
- Hairline borders (`1px`/`1.5px` `--hair`) and soft shadows only; no 3px borders, no offset hard shadows.
- Tricolour stripe: top page edge only; never render a flag or chakra.
- All animation gated by `@media (prefers-reduced-motion: reduce)`.
- Every page usable at 360px width.
- Copy register: microcopy may joke; letters and legal/policy text never do. Footer disclaimer text is verbatim-frozen.
- Dev DB is disposable: after any model change, delete `instance/jkb.db` (it recreates on boot). Never edit migrations — there are none pre-launch.
- Commit after every task with the message given in the task.

## File Structure (created/modified across the plan)

```
app/config.py                 modify: DAILY_CAP default 0, BATCH_PACE, SPONSOR_BUNDLES
app/models.py                 modify: Order.promised_date, Order.sponsored_request; new Sponsorship
app/services/util.py          modify: uncapped consume_slot, promised_post_date()
app/services/sharecard.py     modify: palette+fonts restyle
app/services/posters.py       create: Pillow poster PNG renderer
app/routes/public.py          modify: eta context, sponsor routes, poster route, cant-pay
app/routes/admin.py           modify: sponsor tab/confirm, sponsored-request approve
app/letter_templates.py       (unchanged)
app/data/fuel.json            modify: add source, updated_at
app/data/posters.json         create: poster registry
app/static/css/style.css      rewrite (ported from mockup + new page sections)
app/static/js/main.js         modify: signature mirror, chips, thunk, share, count-up
app/static/fonts/             create: PlayfairDisplay[wght].ttf, Caveat[wght].ttf
app/templates/_art.html       create: SVG macro library
app/templates/base.html       rewrite: masthead/ears/stripe/ticker/footer
app/templates/index.html      rewrite: v5 section order
app/templates/write.html      modify: picker seals, chips, ETA, signature preview
app/templates/pay.html        modify: stamp-frame QR, share moment
app/templates/status.html     modify: journey timeline, thunk, share grid
app/templates/sponsor.html    create
app/templates/admin/queue.html  modify: sponsor tab
app/templates/emails/*.html   modify palette; create sponsor_receipt.html
app/templates/pages/refunds.html  modify: promised-date SLA copy
scripts/smoke_test.py         modify: new checks each task
scripts/sla_check.py          modify: promised_date basis
```

---

### Task 1: Design tokens, fonts, base layout (stripe, masthead + ears, ticker, footer)

**Files:**
- Modify: `app/templates/base.html` (full rewrite of header/footer chrome; keep flash/nav/block structure)
- Modify: `app/static/css/style.css` (full rewrite of `:root` + chrome sections; page-specific sections from the old file that later tasks replace may temporarily remain — they get overwritten in Tasks 3–7)
- Modify: `scripts/smoke_test.py`
- Reference: mockup `<style>` lines and body — masthead/ticker/footer markup ports almost verbatim

**Interfaces:**
- Produces: CSS classes `.mast`, `.mast-grid`, `.ear`, `.ornament`, `.airmail`, `.ticker`, `.kicker`, `.btn`, `.btn.verm`, `.btn.ghost`, `.wrap`, `.mono`, `.hand`, `section.band`, `.band h3` — used by every later template task. Jinja blocks unchanged: `{% block content %}`, `{% block scripts %}`, `{% block head_extra %}`, `{% block title %}`.

- [ ] **Step 1: Add failing smoke checks**

In `scripts/smoke_test.py`, immediately after the `check("DIY kit PDF", ...)` line, insert:

```python
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
./.venv/Scripts/python scripts/smoke_test.py
```
Expected: `FAIL: masthead students line`

- [ ] **Step 3: Rewrite `base.html` chrome**

Replace the Google Fonts link with:

```html
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;0,800;0,900;1,600&family=Caveat:wght@600&family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
```

Replace everything from `<div class="airmail-stripe">` through `</header>` and the marquee block with the mockup's `<div class="airmail">`, `<header class="mast">…</header>` (both ears, ornament rule) and ticker markup, with these Jinja deltas:

```html
<nav>
  <a href="{{ url_for('public.write') }}">WRITE A LETTER</a>
  <a href="{{ url_for('public.sponsor') if 'public.sponsor' in url_map_endpoints else '#' }}">SPONSOR</a>
  <a href="{{ url_for('public.ledger') }}">LEDGER</a>
  <a href="{{ url_for('public.diy') }}">DIY KIT</a>
  <a href="{{ url_for('public.about') }}">ABOUT</a>
</nav>
```

Until Task 8 exists, hardcode the sponsor link as `{{ url_for('public.index') }}#sponsor` (Task 8 swaps it to `url_for('public.sponsor')`). Ticker content (one `{% for _ in range(3) %}` loop over):

```html
<span><b>{{ "{:,}".format(letters_count()) }}</b> LETTERS AND COUNTING</span>
<span>A LETTER IS A PROTEST THAT NEEDS NO PERMIT</span>
<span>DISTANCE IS NOT SILENCE</span>
<span>POSTED · PHOTOGRAPHED · TRACKED</span>
```

Footer: port the mockup footer (double rule); disclaimer paragraph text unchanged; keep the policy-links nav and grievance line from the old footer, restyled with class `mono`. Keep flashes, CF beacon, and `main.js` script tag as-is.

- [ ] **Step 4: Rewrite `style.css` `:root` + chrome**

Copy from the mockup `<style>`: the `:root` block (all tokens from Global Constraints), `body` + grain `body::after`, `.mono`, `.hand`, `.wrap`, `.airmail`, `.mast*`/`.ear`/`.ornament` (+ its `@media (max-width:760px)`), `.ticker*`, `@keyframes tick`, `.kicker`, `.btn*`, `section.band`, `.band h3`, footer styles. Delete the old `.airmail-stripe`, `.masthead*`, `.marquee*` rules and every `var(--maroon-*)`/`#3D0808`/`#6E1010`/`#C1121F`/`#A50F1B` usage in the remaining old sections — where old page sections still reference them, substitute: maroon-950→`var(--ink)`, maroon-800→`var(--ink-soft)`, stamp-red→`var(--verm-deep)`. Keep the old flash/form/table sections functional (restyled properly in later tasks). Add at the end:

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { animation: none !important; transition: none !important; }
}
:focus-visible { outline: 3px solid var(--verm); outline-offset: 2px; }
```

- [ ] **Step 5: Run — expect PASS, then eyeball**

```bash
./.venv/Scripts/python scripts/smoke_test.py
```
Expected: all checks pass. Then `./.venv/Scripts/python run.py`, open http://127.0.0.1:5000 — stripe, ears, ticker, footer render; no maroon. Stop the server.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "redesign: ink-letterpress tokens, fonts, masthead with ears, tricolour stripe, ticker, footer"
```

---

### Task 2: SVG art macro library

**Files:**
- Create: `app/templates/_art.html`
- Modify: `scripts/smoke_test.py`

**Interfaces:**
- Produces Jinja macros (imported as `{% import "_art.html" as art %}`):
  `art.stamp()`, `art.postmark(top, bottom)`, `art.city_postmark(city)`, `art.postbox_ear()`, `art.postmark_ear()`, `art.envelope_ornament()`, `art.hand_underline()`, `art.seal(big, small)`, `art.icon_nib()`, `art.icon_letter()`, `art.icon_check()`, `art.icon_lamp()`, `art.icon_house()`, `art.icon_mailbag()`, `art.icon_bhawan()`. All emit inline `<svg>` with `aria-hidden="true"`.

- [ ] **Step 1: Failing check** — in `smoke_test.py` after the Task-1 block:

```python
    check("art macros render", b"aria-hidden" in r.data and b"<svg" in r.data)
```

- [ ] **Step 2: Run — expect FAIL** (base.html has raw SVGs without aria-hidden yet ⇒ first clause fails).

- [ ] **Step 3: Create `app/templates/_art.html`**

Port the exact SVGs already present in the mockup into macros, adding `aria-hidden="true"` to each `<svg>`: postbox ear + postmark ear (mockup header), stamp + postmark + squiggle (mockup envelope), step icons nib/letter/check (mockup how-it-works), seal (mockup sponsor). Parameterise text:

```jinja
{% macro postmark(top="POSTED", bottom="") %}
<svg aria-hidden="true" width="74" height="74" viewBox="0 0 76 76" fill="none">
  <circle cx="38" cy="38" r="34" stroke="#171512" stroke-width="1.3"/>
  <circle cx="38" cy="38" r="27" stroke="#171512" stroke-width="0.8"/>
  <text x="38" y="35" text-anchor="middle" font-family="IBM Plex Mono" font-size="8.5" fill="#171512">{{ top }}</text>
  <text x="38" y="47" text-anchor="middle" font-family="IBM Plex Mono" font-size="7.5" fill="#171512">{{ bottom }}</text>
</svg>
{% endmacro %}

{% macro city_postmark(city) %}{{ postmark(city|upper|truncate(12, True, ""), "2026") }}{% endmacro %}

{% macro hand_underline() %}
<svg aria-hidden="true" viewBox="0 0 300 14" preserveAspectRatio="none"><path d="M3 9 Q75 3 150 8 T297 6" stroke="#E2401B" stroke-width="4.5" fill="none" stroke-linecap="round"/></svg>
{% endmacro %}
```

New macros not in the mockup — lamp, house, mailbag, bhawan (same stroke grammar: `stroke="#171512" stroke-width="1.4"`, vermilion sub-accent):

```jinja
{% macro icon_lamp() %}
<svg aria-hidden="true" width="42" height="42" viewBox="0 0 44 44" fill="none" stroke="#171512" stroke-width="1.4">
  <path d="M22 6 c5 6 5 12 0 16 c-5 -4 -5 -10 0 -16 z" stroke="#B93511"/>
  <path d="M14 26 h16 M12 32 h20 M18 38 h8 M22 22 v4"/></svg>
{% endmacro %}
{% macro icon_house() %}
<svg aria-hidden="true" width="42" height="42" viewBox="0 0 44 44" fill="none" stroke="#171512" stroke-width="1.4">
  <path d="M8 22 L22 8 L36 22"/><path d="M12 20 v16 h20 v-16"/>
  <rect x="19" y="26" width="6" height="10" stroke="#B93511"/></svg>
{% endmacro %}
{% macro icon_mailbag() %}
<svg aria-hidden="true" width="42" height="42" viewBox="0 0 44 44" fill="none" stroke="#171512" stroke-width="1.4">
  <path d="M12 16 q10 -10 20 0 v2 q-10 4 -20 0 z"/><path d="M10 20 c-2 10 2 18 12 18 s14 -8 12 -18"/>
  <path d="M17 27 h10" stroke="#B93511"/></svg>
{% endmacro %}
{% macro icon_bhawan() %}
<svg aria-hidden="true" width="42" height="42" viewBox="0 0 44 44" fill="none" stroke="#171512" stroke-width="1.4">
  <path d="M6 38 h32 M8 38 v-14 h28 v14 M12 24 v-6 h20 v6"/>
  <path d="M14 38 v-8 M20 38 v-8 M26 38 v-8 M32 38 v-8" stroke-width="1"/>
  <path d="M22 18 v-6 l5 2 v2 l-5 0" stroke="#B93511"/></svg>
{% endmacro %}
```

Then in `base.html`: `{% import "_art.html" as art %}` at top; replace the two hardcoded ear SVGs and the ornament envelope with `{{ art.postbox_ear() }}`, `{{ art.postmark_ear() }}`, `{{ art.envelope_ornament() }}`.

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "redesign: engraved SVG art macro library"`

---

### Task 3: Home page rebuild (v5 order) + fuel/poster data files

**Files:**
- Modify: `app/templates/index.html` (full rewrite), `app/data/fuel.json`, `app/routes/public.py:index`, `app/static/css/style.css` (hero/fuel/plate/steps/tiers/mailbag/posters/sponsor sections), `app/static/js/main.js` (count-up), `scripts/smoke_test.py`
- Create: `app/data/posters.json`

**Interfaces:**
- Consumes: Task 1 chrome classes, Task 2 macros.
- Produces: `posters.json` schema `[{"id","headline","hand_line","theme","caption"}]` and route context `posters` (list of dicts) — reused by Tasks 6, 7, 10. `_fuel()` now returns `{"updated_at": str, "items": [{"date","title","source","url"}]}`.

- [ ] **Step 1: Failing checks** — after the Task-2 check:

```python
    check("hero slogan", b"Mann&nbsp;Ki&nbsp;Baat" in r.data
          and b"Janata&nbsp;Ki&nbsp;Baat" in r.data)
    check("live news desk", b"LIVE" in r.data and b"SOURCED, NOT RUMOURED" in r.data)
    check("no slots scarcity on home", b"slots" not in r.data.lower())
    check("posters on home", b"TAP TO SHARE" in r.data)
    check("sponsor band on home", b"Letters Fund" in r.data)
```

- [ ] **Step 2: Run — expect FAIL** (`hero slogan`).

- [ ] **Step 3: Data files**

`app/data/fuel.json` — new shape (keep the four existing verified items, add `source`; the plan-verified sources are already in each item's `url`):

```json
{
  "updated_at": "22 JUL · 09:00 IST",
  "items": [
    {"date": "21 JUL", "title": "Youth-led movement vows to continue protests after police crackdown", "source": "NPR", "url": "https://www.npr.org/2026/07/21/g-s1-134722/indias-youth-led-cockroach-movement-vows-to-continue-protest-after-police-crackdown"},
    {"date": "20 JUL", "title": "Thousands march on Parliament; ~180 injured in police action", "source": "AL JAZEERA", "url": "https://www.aljazeera.com/news/2026/7/20/police-attack-cockroach-activists-as-thousands-march-on-indian-parliament"},
    {"date": "18 JUL", "title": "Sonam Wangchuk hospitalised on day 21 of hunger strike", "source": "WIRE REPORTS", "url": "https://en.wikipedia.org/wiki/2026_Delhi_Jantar_Mantar_protests"},
    {"date": "JUN", "title": "NEET-UG 2026 cancelled after confirmed paper leak; CBI inquiry ordered", "source": "NBC", "url": "https://www.nbcnews.com/world/asia/india-cockroach-party-protest-march-modi-exams-delhi-rcna588364"}
  ]
}
```

`app/data/posters.json`:

```json
[
  {"id": "cant-march", "headline": "Can't march?|Mail.", "hand_line": "— 2 minutes. ₹59. On the record.", "theme": "light",
   "caption": "Can't march? Mail. 2 minutes and ₹59 puts you on the record. janatakibaat.in #JanataKiBaat"},
  {"id": "sunn-li", "headline": "\"Mann Ki Baat sunn li.|Janata Ki Baat bhej di.\"", "hand_line": "", "theme": "dark",
   "caption": "Mann Ki Baat sunn li. Janata Ki Baat bhej di. 📮 janatakibaat.in"},
  {"id": "mailbag-count", "headline": "{count} letters|can't be scrolled past.", "hand_line": "— yours makes {next}", "theme": "light",
   "caption": "{count} letters to the Education Ministry can't be scrolled past. Yours makes {next}. janatakibaat.in"}
]
```

(`|` = line break; `{count}`/`{next}` substituted at render.)

In `public.py`, update `_fuel()` to return the dict (fallback `{"updated_at": "", "items": []}` on error) and add:

```python
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


@bp.get("/")
def index():
    return render_template("index.html", fuel=_fuel(), posters=_posters())
```

- [ ] **Step 4: Rewrite `index.html` + port section CSS**

Port from the mockup, section by section, in v5 order: hero (slogan `h2` with `quiet`/`loud` spans + `{{ art.hand_underline() }}`; envelope card using `art.stamp()`/`art.postmark("POSTED", now)`; stats row with `{{ "{:,}".format(letters_count()) }}` and `data-countup` attribute) → fuel desk (`deskhead` with LIVE pulse + `{{ fuel.updated_at }}`; newswire `{% for _ in range(3) %}{% for it in fuel["items"] %}` items linking `it.url`) → manifesto plate (copy verbatim from mockup) → how-it-works (three `.step` with `art.icon_nib()/icon_letter()/icon_check()`) → tiers (three `.tier` cards; prices/breakdowns from `TIERS` config as before) → proof wall (dark band; loop `{% for shot in batch_shots %}` — route passes `batch_shots = sorted((Path(app.static_folder)/"batches").glob("*.jpg"))` if the dir exists else `[]`; when empty render the three styled placeholder `.shot` divs from the mockup) → posters (`{% for p in posters %}` → `.poster{% if p.theme=='dark' %} dark{% endif %}` with `data-poster-id`, `data-caption`, headline split on `|`) → sponsor band (seal + copy + fund counts: `sponsored_count = int(-(totals.get('fund',0)) // 59)` — for now hardcode `0 sponsored so far`; Task 8 wires the real number) → footer from base. Delete the old waitlist section and all `slots_left()` usage in this template. Copy the corresponding CSS blocks from the mockup `<style>` into `style.css` (`.hero*`, `.env*`, `.fuel*`, `.live*`, `.newswire*`, `.plate*`, `.steps/.step`, `.tiers/.tier`, `.mailbag/.shots/.shot`, `.posters/.poster`, `.sponsor`, plus the `@media (max-width:860px)` block), replacing the old equivalents.

In `main.js` add the count-up (before the closing IIFE):

```js
  /* ---------- home: counter tick-up, once per view ---------- */
  document.querySelectorAll("[data-countup]").forEach(function (el) {
    var target = parseInt(el.dataset.countup.replace(/,/g, ""), 10);
    if (!target || sessionStorage.getItem("jkb-counted")) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    sessionStorage.setItem("jkb-counted", "1");
    var start = Math.max(0, target - 40), cur = start;
    var t = setInterval(function () {
      cur += Math.ceil((target - cur) / 8) || 1;
      el.textContent = cur.toLocaleString("en-IN");
      if (cur >= target) clearInterval(t);
    }, 40);
  });
```

- [ ] **Step 5: Run — expect PASS; eyeball desktop + 360px** (`run.py`, browser devtools responsive mode).
- [ ] **Step 6: Commit** — `git add -A && git commit -m "redesign: home page in v5 order with live news desk, proof wall, posters, sponsor band"`

---

### Task 4: Uncapped intake + promised-date promise

**Files:**
- Modify: `app/config.py`, `app/models.py`, `app/services/util.py`, `app/routes/public.py`, `app/routes/admin.py:confirm`, `app/templates/pages/refunds.html`, `scripts/sla_check.py`, `.env.example`, `.env`, `scripts/smoke_test.py`

**Interfaces:**
- Produces: `util.promised_post_date() -> datetime.date` (live queue estimate); `Order.promised_date` (Date, nullable, set at admin confirm); config `BATCH_PACE: int = 50`, `DAILY_CAP` default `0` (0 = uncapped).
- Consumed by: Task 5 (write page ETA line), Task 7 (status), `sla_check.py`.

- [ ] **Step 1: Failing checks**

The existing final smoke section ("cap full -> waitlist") breaks under uncapped defaults. Replace that whole section (from `# --- cap full -> waitlist ---` through the waitlist check) with:

```python
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
```

- [ ] **Step 2: Run — expect FAIL** (`promised_date set at confirm` → AttributeError, or `uncapped` check).

- [ ] **Step 3: Implement**

`config.py`: `DAILY_CAP = int(os.environ.get("DAILY_CAP", "0"))` and add `BATCH_PACE = int(os.environ.get("BATCH_PACE", "50"))`. Update `.env.example` (and local `.env`): `DAILY_CAP=0` with comment `# 0 = uncapped (launch decision); set >0 to re-enable the daily brake`, plus `BATCH_PACE=50`.

`models.py` `Order`: add

```python
    promised_date = db.Column(db.Date, nullable=True)
```

`services/util.py`:

```python
import math


def consume_slot():
    """Uncapped when DAILY_CAP<=0 (launch decision, spec §8); the guarded
    UPDATE below is the re-enable path."""
    if current_app.config["DAILY_CAP"] <= 0:
        return True
    row = _cap_row()
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
```

(`_cap_row` must use `current_app.config["DAILY_CAP"] or 50` for `cap_limit` so a capped-mode row never gets limit 0.)

`public.py`: `_render_write` gains `eta=promised_post_date()` in its context (import it); the template consumes it in Task 5 — for this task, add the line to the *existing* write template near the submit button so the smoke check passes:

```html
<p class="small mono">In today's mailbag — posts by {{ eta.strftime('%d %b') }} ·
   posted by that date or a full automatic refund.</p>
```

and delete the old `Today's slots: {{ slots_left() }}` line there.

`admin.py:confirm`, after `order.serial_no = next_serial()`:

```python
    from ..services.util import promised_post_date
    order.promised_date = promised_post_date()
```

`scripts/sla_check.py`: replace the cutoff query with

```python
        overdue = [
            o for o in Order.query.filter(
                Order.status.in_(["confirmed", "printed"])).all()
            if o.promised_date
            and utcnow().date() > o.promised_date + timedelta(days=2)
        ]
```

and update the print line to include `o.promised_date`.

`pages/refunds.html`: replace the "2 working days"/"5 days" paragraphs with: promise = *"posted by the date shown when you ordered"*; automatic full refund if posting runs more than 2 working days past that date; same UPI rail; ledger entry. Keep the rest.

Delete the dev DB so the new column exists: `rm -f instance/jkb.db`.

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: uncapped intake with promised-post-date promise (DAILY_CAP=0, BATCH_PACE)"`

---

### Task 5: Write page — letterhead picker, tip chips, ink signature, city postmark

**Files:**
- Modify: `app/templates/write.html`, `app/static/css/style.css`, `app/static/js/main.js`, `scripts/smoke_test.py`

**Interfaces:**
- Consumes: `art.seal/icon_nib/icon_lamp/icon_house`, `art.city_postmark`, `eta` (Task 4), existing form fields/names (unchanged — backend validation untouched), template JSON script `#tpl-data`.
- Produces: tip input stays `name="tip"` (hidden `<input type="hidden" id="f-tip" name="tip">` driven by chips) so `_validate_write_form` is unchanged.

- [ ] **Step 1: Failing checks** — after the Task-4 block:

```python
    r = client.get("/write")
    check("tip chips", b"cutting chai" in r.data and b"full tiffin" in r.data)
    check("ink signature slot", b'data-lp="sig"' in r.data)
    check("city postmark slot", b"city-postmark" in r.data)
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

`write.html` changes (structure/two-pane kept):
1. Template picker options get a seal: inside each `.tpl-option`, before the text span:
   `{% set seals = {'neet-accountability': art.icon_nib(), 'solidarity-humane-treatment': art.icon_lamp(), 'cost-to-families': art.icon_house()} %}` at top, then `<span class="tpl-seal">{{ seals[t.slug] }}</span>`.
2. Replace the tip slider field with:

```html
<div class="field">
  <label>Add a chai for the volunteer (optional)</label>
  <div class="chips" id="tip-chips">
    {% for amt, lbl in [(0, "no chai"), (10, "cutting chai"), (20, "chai + Parle-G"), (50, "full tiffin")] %}
    <button type="button" class="chip {% if (values.tip or 0)|int == amt %}on{% endif %}"
            data-tip="{{ amt }}">₹{{ amt }} <small>{{ lbl }}</small></button>
    {% endfor %}
    <button type="button" class="chip" data-tip="custom">custom</button>
    <input type="number" id="tip-custom" min="0" max="{{ cfg.TIP_MAX }}" step="10"
           placeholder="₹" style="display:none;width:90px;">
  </div>
  <input type="hidden" id="f-tip" name="tip" value="{{ values.tip or 0 }}">
  <div class="hint">Every rupee lands in the public Letters Fund — it posts
    letters for people who can't pay.</div>
</div>
```

3. Beside the page heading add `<span class="city-postmark" id="city-postmark" data-empty="1">{{ art.city_postmark("YOUR CITY") }}</span>`.
4. In the preview signature block, wrap the name: `<span class="hand sig" data-lp="sig">Your Name</span>` above the printed `<strong data-lp="name2">` line (the letter PDF is unchanged — the ink signature is a screen-only personal touch; keep the printed name line too).
5. Keep the ETA line from Task 4.

`style.css` additions:

```css
.chips { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.chip { font-family: Inter, sans-serif; font-weight: 600; font-size: 14.5px;
  background: var(--card); color: var(--ink); border: 1.5px solid var(--hair);
  border-radius: 999px; padding: 9px 16px; cursor: pointer;
  transition: transform .15s ease, border-color .15s ease; }
.chip small { font-family: 'IBM Plex Mono', monospace; font-weight: 400;
  font-size: 11px; color: var(--stone); margin-left: 4px; }
.chip:hover { transform: translateY(-2px); }
.chip.on { border-color: var(--verm-deep); background: var(--paper-deep);
  box-shadow: 0 4px 12px rgba(23,21,18,.10); }
.chip.on small { color: var(--verm-deep); }
.tpl-seal { flex-shrink: 0; margin-right: 4px; }
.sig { font-size: 30px; color: var(--verm-deep); display: inline-block;
  min-height: 34px; transform: rotate(-2deg); }
.city-postmark { display: inline-block; vertical-align: middle; margin-left: 14px;
  opacity: .35; transition: opacity .3s; }
.city-postmark.inked { opacity: .9; }
```

`main.js` — in the write-page block (where `nameInput`/`cityInput` exist), extend `render()`:

```js
      var sig = q('[data-lp="sig"]');
      if (sig) sig.textContent = name === "Your Name" ? "" : name;
```

and after the render wiring add:

```js
    /* city postmark inks in as you type */
    var pm = document.getElementById("city-postmark");
    if (pm && cityInput) {
      cityInput.addEventListener("input", function () {
        var c = cityInput.value.trim();
        pm.classList.toggle("inked", c.length > 1);
        var t = pm.querySelector("svg text");
        if (t) t.textContent = (c || "YOUR CITY").toUpperCase().slice(0, 12);
      });
    }
    /* tip chips */
    var chipBox = document.getElementById("tip-chips");
    if (chipBox) {
      var hidden = document.getElementById("f-tip");
      var custom = document.getElementById("tip-custom");
      chipBox.querySelectorAll(".chip").forEach(function (ch) {
        ch.addEventListener("click", function () {
          chipBox.querySelectorAll(".chip").forEach(function (o) { o.classList.remove("on"); });
          ch.classList.add("on");
          if (ch.dataset.tip === "custom") { custom.style.display = "inline-block"; custom.focus(); }
          else { custom.style.display = "none"; hidden.value = ch.dataset.tip; }
        });
      });
      custom.addEventListener("input", function () { hidden.value = custom.value || 0; });
    }
```

Remove the old `#f-tip`-range slider JS block.

- [ ] **Step 4: Run — expect PASS; eyeball** the live signature + postmark inking at http://127.0.0.1:5000/write.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "redesign: write page with letterhead seals, tip chips, live ink signature, city postmark"`

---

### Task 6: Pay page — stamp-frame QR, booking slip, share moment

**Files:**
- Modify: `app/templates/pay.html`, `app/static/css/style.css`, `app/routes/public.py:pay`, `scripts/smoke_test.py`

**Interfaces:**
- Consumes: `_posters()` (Task 3) — route passes `poster=_posters()[0]`.

- [ ] **Step 1: Failing checks** — inside the existing pay-page section of the smoke test, extend the pay assertions:

```python
    check("stamp-frame QR", b"stamp-frame" in r.data)
    check("share moment on pay", b"Tell one person" in r.data)
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

`public.py:pay` — add `poster=(_posters() or [None])[0]` to the render context. `pay.html`: wrap the QR `<div class="qr-frame">` → `<div class="qr-frame stamp-frame">`; set the amount heading class to a new `.pay-amount` (Playfair 900); render the order code inside `.slip`; after the UTR form add:

```html
<div class="poster" data-poster-id="{{ poster.id }}" data-caption="{{ poster.caption }}" style="max-width:340px;margin-top:26px;">
  <span class="share-tag">TAP TO SHARE ↗</span>
  <h5>Your letter is being matched.<br><span style="color:var(--verm-deep);">Tell one person while you wait.</span></h5>
</div>
{% endif %}
```

(only when `poster`). CSS:

```css
.stamp-frame { border: 2px dashed var(--verm-deep); outline: 6px solid #fff;
  outline-offset: -8px; background: #fff; padding: 18px; border-radius: 3px;
  box-shadow: 0 14px 40px rgba(23,21,18,.14); width: fit-content; }
.pay-amount { font-family: 'Playfair Display', serif; font-weight: 900;
  font-size: clamp(40px, 6vw, 54px); color: var(--verm-deep); }
.slip { font-family: 'IBM Plex Mono', monospace; background: var(--paper-deep);
  border: 1px solid var(--hair); padding: 6px 12px; font-weight: 600;
  letter-spacing: .06em; display: inline-block; }
```

Update all three existing `class="pay-code"` usages to `class="slip"`: two in `pay.html` (the order-code line and the "Keep {code} in the payment note" line) and one in `status.html` (the tracking-number span, at the `India Post tracking:` line — Task 7 rewrites the rest of that file, but this specific span is in scope here since it's a straight class rename, not a journey-timeline concern). Delete the old `.pay-code` CSS rule; there is no alias.

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "redesign: pay page stamp-frame QR, booking slip, mid-flow share moment"`

---

### Task 7: Status page — ownership header, envelope journey, postmark thunk, share grid

**Files:**
- Modify: `app/templates/status.html`, `app/static/css/style.css`, `app/static/js/main.js`, `app/routes/public.py:status`, `scripts/smoke_test.py`

**Interfaces:**
- Consumes: `art.icon_nib/icon_letter/icon_mailbag/icon_check/icon_bhawan`, `art.city_postmark`, `art.postmark`, captions list (existing), `order.promised_date`.

- [ ] **Step 1: Failing checks** — in the post-proof section of the smoke test (after `status shows proof + tracking`):

```python
    check("ownership header", b"letter to the Education Ministry" in r.data)
    check("journey timeline", b"journey" in r.data)
    check("thunk animation hook", b"postmark-thunk" in r.data)
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

`status.html`:
- Header: `<h1>Letter #{{ "{:,}".format(order.serial_no) }} — {{ order.name.split(' ')[0] }}'s letter to the Education Ministry</h1>` (unserialed: `Your letter to the Education Ministry`), followed by `{{ art.city_postmark(order.city.split(',')[0]) }}`.
- Replace `.timeline` markup with `.journey`: five `<li>` milestones, each `art.icon_nib() / icon_letter() / icon_mailbag() / icon_check() / icon_bhawan()` + label (Queued / Payment confirmed / Printed / Posted / Delivered) + the existing per-state detail lines; `li.done` gets vermilion icon strokes via CSS filter class. Reuse the existing `reached` mapping logic verbatim.
- When `order.is_paid`, above the timeline: `<div class="postmark-thunk" data-thunk="{{ order.public_code }}">{{ art.postmark("POSTED", (order.posted_at or order.confirmed_at).strftime("%d %b %Y")|upper) }}</div>` and the line `<p class="mono small">You are letter #{{ "{:,}".format(order.serial_no) }} of a mailbag that can't be scrolled past.</p>`.
- Proof image: wrap in `<figure class="proof-mount">` (corner mounts via CSS `::before/::after` + inner span corners).
- Share section: keep the two card `<img>`s and captions, restyled with `.posters` classes; keep `#share-btn`.
- If `order.promised_date` and not yet posted: `<p class="mono small">Promised in the mail by {{ order.promised_date.strftime('%d %b %Y') }}.</p>`

CSS:

```css
.journey { list-style: none; padding: 0; margin: 26px 0; max-width: 620px; }
.journey li { display: flex; gap: 16px; align-items: flex-start;
  padding: 0 0 22px 0; border-left: 0; position: relative; }
.journey li::before { content: ""; position: absolute; left: 20px; top: 44px;
  bottom: -2px; width: 1.5px; background: var(--hair); }
.journey li:last-child::before { display: none; }
.journey li svg { flex-shrink: 0; background: var(--card);
  border: 1.5px solid var(--hair); border-radius: 50%; padding: 8px;
  width: 42px; height: 42px; }
.journey li.done svg { border-color: var(--verm-deep); }
.journey .step-name { font-family: 'IBM Plex Mono', monospace; font-size: 13px;
  font-weight: 600; letter-spacing: .1em; text-transform: uppercase; }
.journey li.done .step-name { color: var(--verm-deep); }
.journey .step-detail { font-size: 14px; color: var(--ink-soft); }
.postmark-thunk { display: inline-block; }
.postmark-thunk.play { animation: thunk .45s cubic-bezier(.2, 2.2, .4, 1) both; }
@keyframes thunk {
  0% { transform: scale(2.4) rotate(-18deg); opacity: 0; }
  60% { transform: scale(.94) rotate(-7deg); opacity: 1; }
  100% { transform: scale(1) rotate(-8deg); opacity: 1; }
}
.proof-mount { margin: 0; display: inline-block; position: relative; padding: 14px; background: var(--card); border: 1px solid var(--hair); box-shadow: 0 14px 40px rgba(23,21,18,.14); }
.proof-mount img { display: block; max-width: 100%;
  filter: grayscale(1) contrast(1.05); }
.proof-mount::after { content: ""; position: absolute; inset: 14px;
  background: linear-gradient(125deg, rgba(226,64,27,.22), transparent 60%);
  pointer-events: none; }
```

`main.js`:

```js
  /* ---------- status: postmark thunk, once per order ---------- */
  var thunk = document.querySelector(".postmark-thunk[data-thunk]");
  if (thunk) {
    var key = "jkb-thunk-" + thunk.dataset.thunk;
    if (!sessionStorage.getItem(key)
        && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      sessionStorage.setItem(key, "1");
      requestAnimationFrame(function () { thunk.classList.add("play"); });
    }
  }
```

- [ ] **Step 4: Run — expect PASS; eyeball the thunk** on a confirmed order's status page (fresh tab = fresh sessionStorage).
- [ ] **Step 5: Commit** — `git add -A && git commit -m "redesign: status page ownership header, envelope journey, postmark thunk, mounted proof"`

---

### Task 8: Sponsor-a-Letter — model, public flow, admin confirm, email

**Files:**
- Modify: `app/config.py`, `app/models.py`, `app/services/util.py:gen_public_code`, `app/routes/public.py`, `app/routes/admin.py`, `app/templates/admin/queue.html`, `app/templates/base.html` (nav), `app/templates/index.html` (real sponsored count), `scripts/smoke_test.py`
- Create: `app/templates/sponsor.html`, `app/templates/sponsor_pay.html`, `app/templates/emails/sponsor_receipt.html`

**Interfaces:**
- Produces: model `Sponsorship(id, public_code "JKS-…", email, bundle_qty, amount, status in [pending_payment, utr_submitted, confirmed, expired], utr, created_at, utr_at, confirmed_at)` with property `total -> amount`; routes `public.sponsor` (GET), `public.sponsor_create` (POST), `public.sponsor_pay` (GET `/sponsor/pay/<code>`), `public.sponsor_qr`, `public.sponsor_utr` (POST); `admin.sponsor_confirm` (POST `/admin/sponsor/<id>/confirm`); config `SPONSOR_BUNDLES = [(1, 59), (3, 177), (5, 295), (10, 590)]`; helper `util.fund_balance() -> float` (sum of ledger `fund` + `tip` entries).
- Consumed by: Task 9 (fund draw-down), Task 3's sponsor band (real count wired here).

- [ ] **Step 1: Failing checks** — append before the final `print`:

```python
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
```

- [ ] **Step 2: Run — expect FAIL** (404 on `/sponsor`).

- [ ] **Step 3: Implement**

`config.py`: `SPONSOR_BUNDLES = [(1, 59), (3, 177), (5, 295), (10, 590)]`.

`models.py`:

```python
class Sponsorship(db.Model):
    __tablename__ = "sponsorships"

    id = db.Column(db.Integer, primary_key=True)
    public_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    email = db.Column(db.String(254), nullable=False)
    bundle_qty = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending_payment")
    utr = db.Column(db.String(40), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=utcnow)
    utr_at = db.Column(db.DateTime, nullable=True)
    confirmed_at = db.Column(db.DateTime, nullable=True)

    @property
    def total(self):
        return self.amount
```

`util.py`: generalise the code generator and add the fund helper:

```python
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
```

`public.py` (new section; `payments.upi_uri`/`qr_png` already only use `.total` and `.public_code`, so they accept a `Sponsorship` unchanged):

```python
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
```

`admin.py`:

```python
@bp.post("/sponsor/<int:s_id>/confirm")
@admin_required
def sponsor_confirm(s_id):
    from ..models import Sponsorship
    s = db.session.get(Sponsorship, s_id)
    if s is None or s.status != "utr_submitted":
        flash("Sponsorship not awaiting confirmation.", "error")
        return redirect(url_for("admin.queue", tab="sponsor"))
    s.status, s.confirmed_at = "confirmed", utcnow()
    db.session.add(LedgerEntry(type="fund", amount=s.amount,
                               order_ref=s.public_code,
                               note=f"sponsored {s.bundle_qty} letter(s)"))
    db.session.commit()
    mailer.send_email(
        s.email, f"Receipt — you sponsored {s.bundle_qty} letter(s)",
        render_template("emails/sponsor_receipt.html", s=s),
    )
    flash(f"{s.public_code} confirmed — ₹{s.amount} into the Letters Fund.", "success")
    return redirect(url_for("admin.queue", tab="sponsor"))
```

In `admin.py:queue`, add to the tabs dict a `"sponsor"` entry (`Sponsorship.query.filter_by(status="utr_submitted")` — import at top) and pass its rows separately as `sponsorships` when `tab == "sponsor"`; in `admin/queue.html` add the tab link + a simple table (code / email / qty / ₹ / UTR / Confirm ✓ button posting to `admin.sponsor_confirm`).

`sponsor.html`: extends base; seal hero (`art.seal("₹59", "SPONSOR A LETTER")`), fund pitch copy from the mockup sponsor band, live `₹{{ "%.2f"|format(fund) }} in the fund · {{ sponsored }} letters sponsored`, bundle cards (loop `bundles`) as radio-styled `.tier` cards with a single email field + submit `Sponsor {{ qty }} →`, two FAQ `details` (money sits in the public ledger fund; free letters are claimed on the write page). `sponsor_pay.html`: clone of `pay.html`'s stamp-frame QR + UTR form with `s` in place of `order` and the sponsor endpoints.

Wire the real count into `index.html`'s sponsor band and swap the base-nav SPONSOR link to `{{ url_for('public.sponsor') }}`. Also extend `scripts/expire_orders.py` to expire stale `Sponsorship` rows the same way (24 h, `pending_payment` only).

Delete `instance/jkb.db` (new table).

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: sponsor-a-letter flow (bundles, UPI, admin confirm, Letters Fund ledger)"`

---

### Task 9: "I can't pay" — sponsored letters drawn from the fund

**Files:**
- Modify: `app/models.py` (one column), `app/templates/write.html`, `app/routes/public.py:write_submit`, `app/routes/admin.py:confirm`, `app/templates/admin/order.html`, `scripts/smoke_test.py`

**Interfaces:**
- Produces: `Order.sponsored_request` (Boolean, default False). Sponsored orders: `amount=0`, `tip=0`, `status='utr_submitted'` (lands straight in the admin Confirm tab), redirect to status page. Admin confirm draws the letter's real cost from the fund: ledger entry `type='fund', amount=-(tier price)`.

- [ ] **Step 1: Failing checks** — after the sponsor-flow block:

```python
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
    r = client.post(f"/admin/order/{osp_id}/confirm")
    with app.app_context():
        check("fund debited for sponsored letter", LedgerEntry.query.filter_by(
            type="fund", order_ref=code_sp).filter(LedgerEntry.amount < 0).count() == 1)
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

`models.py` `Order`: `sponsored_request = db.Column(db.Boolean, nullable=False, default=False)`.

`write.html`, below the tier radios:

```html
<div class="field">
  <label class="chip" style="display:inline-flex;gap:8px;align-items:center;">
    <input type="checkbox" name="cant_pay" value="on"
           {% if values.cant_pay %}checked{% endif %}>
    I can't pay — post mine from the Letters Fund
  </label>
  <div class="hint">Sponsored letters go out when the fund covers them —
    first asked, first posted. No questions, no means test.</div>
</div>
```

`public.py:write_submit` — capture `cant_pay = request.form.get("cant_pay") == "on"` in `_validate_write_form` values; after building the order, before `db.session.add`:

```python
    if values["cant_pay"]:
        order.amount = 0
        order.tip = 0
        order.sponsored_request = True
        order.status = "utr_submitted"
```

and after commit, sponsored orders skip the pay redirect:

```python
    if order.sponsored_request:
        flash("You're in the queue — your letter posts as soon as the "
              "Letters Fund covers it. Watch this page.", "success")
        return redirect(url_for("public.status", code=order.public_code))
```

(Also skip the `order_received` pay-link email for these — send it with the status link as `pay_url` replaced by the status URL.)

`admin.py:confirm` — replace the flat fee/tip ledger block with:

```python
    if order.sponsored_request:
        tier_price = current_app.config["TIERS"][order.tier]["price"]
        db.session.add(LedgerEntry(type="fund", amount=-tier_price,
                                   order_ref=order.public_code,
                                   note="sponsored letter (fund draw)"))
    else:
        db.session.add(LedgerEntry(type="fee", amount=order.amount,
                                   order_ref=order.public_code,
                                   note=f"{order.tier} fee"))
        if order.tip:
            db.session.add(LedgerEntry(type="tip", amount=order.tip,
                                       order_ref=order.public_code,
                                       note="chai for the volunteer"))
```

In `admin/order.html` and the queue rows, show a `FUND` mono tag when `order.sponsored_request` (so the operator can check `fund_balance()` — display it in the queue header line: `fund ₹{{ "%.2f"|format(fund) }}`, passed from the queue route via `util.fund_balance()`).

Delete `instance/jkb.db` (new column).

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "feat: can't-pay letters drawn from the Letters Fund"`

---

### Task 10: Bundled fonts, poster PNGs + share endpoints, share-card restyle

**Files:**
- Create: `app/static/fonts/` (two TTFs), `app/services/posters.py`
- Modify: `app/services/sharecard.py`, `app/routes/public.py`, `app/static/js/main.js`, `scripts/smoke_test.py`

**Interfaces:**
- Produces: route `GET /posters/<poster_id>.png` (1080×1350 PNG, disk-cached in `CARD_CACHE_DIR`); `posters.render_poster(poster: dict) -> Path`; sharecard palette constants renamed to `BAND_BG/STAMP_RED/PAPER/AGED/INK`; font resolution order: bundled TTFs first, then system fallbacks.

- [ ] **Step 1: Download fonts** (variable TTFs from the google/fonts repo, OFL-licensed):

```bash
mkdir -p app/static/fonts
curl -L -o "app/static/fonts/PlayfairDisplay.ttf" "https://github.com/google/fonts/raw/main/ofl/playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"
curl -L -o "app/static/fonts/Caveat.ttf" "https://github.com/google/fonts/raw/main/ofl/caveat/Caveat%5Bwght%5D.ttf"
ls -la app/static/fonts
```

Expected: two files, each >100 KB. If the download fails, stop and report — do not substitute other fonts.

- [ ] **Step 2: Failing checks** — after the can't-pay block:

```python
    # --- posters + restyled cards ---
    r = client.get("/posters/cant-march.png")
    check("poster png", r.status_code == 200 and r.data[:8] == b"\x89PNG\r\n\x1a\n")
    r = client.get("/posters/nope.png")
    check("unknown poster 404", r.status_code == 404)
    src = (ROOT / "app" / "services" / "sharecard.py").read_text(encoding="utf-8")
    for hexcode in ["3D0808", "C1121F"]:
        check(f"no maroon {hexcode} in sharecard", hexcode not in src)
```

- [ ] **Step 3: Run — expect FAIL** (404 on poster png ⇒ first check fails).

- [ ] **Step 4: Implement**

`app/services/posters.py`:

```python
"""Spread-the-word poster PNGs (spec §6): 1080×1350, Ink & Letterpress,
rendered once per (id, letters-count) and cached to disk."""
from pathlib import Path

from flask import current_app
from PIL import Image, ImageDraw, ImageFont

PAPER = "#F7F3EC"
CARD = "#FBF8F2"
INK = "#171512"
VERM = "#E2401B"
VERM_DEEP = "#B93511"

W, H = 1080, 1350


def _font(name, size, variation=None):
    path = Path(current_app.root_path) / "static" / "fonts" / name
    f = ImageFont.truetype(str(path), size)
    if variation:
        try:
            f.set_variation_by_name(variation)
        except OSError:
            pass
    return f


def render_poster(poster):
    cache = Path(current_app.config["CARD_CACHE_DIR"])
    key = "".join(c for c in (poster["headline"] + poster["hand_line"])
                  if c.isdigit())
    path = cache / f"poster-{poster['id']}-{key}.png"
    if path.exists():
        return path

    dark = poster["theme"] == "dark"
    bg, fg = (INK, PAPER) if dark else (PAPER, INK)
    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    head = _font("PlayfairDisplay.ttf", 92, "Black")
    hand = _font("Caveat.ttf", 58, "SemiBold")

    d.rectangle([40, 40, W - 40, H - 40], outline=VERM_DEEP, width=3)
    y = 200
    for i, line in enumerate(poster["headline"].split("|")):
        color = VERM if (i == len(poster["headline"].split("|")) - 1 and not dark) else fg
        d.text((90, y), line.strip('"'), font=head, fill=color)
        y += 118
    if poster["hand_line"]:
        d.text((90, y + 60), poster["hand_line"], font=hand, fill=VERM_DEEP if not dark else VERM)
    d.text((90, H - 150), "JANATAKIBAAT.IN", font=_font("PlayfairDisplay.ttf", 40, "Bold"),
           fill=VERM if dark else VERM_DEEP)
    d.text((90, H - 95), "THE PEOPLE'S POST — FROM THE STUDENTS, FOR THE STUDENTS",
           font=_font("PlayfairDisplay.ttf", 24), fill=fg)

    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG")
    return path
```

`public.py`:

```python
@bp.get("/posters/<poster_id>.png")
def poster_png(poster_id):
    from ..services import posters as poster_svc
    match = [p for p in _posters() if p["id"] == poster_id]
    if not match:
        abort(404)
    return send_file(poster_svc.render_poster(match[0]), mimetype="image/png")
```

`sharecard.py` restyle — palette rename + swap, layout unchanged. Share cards have no hand-lettering (that's poster-only, rendered separately above) — do not introduce Caveat here. Replace the constants block:

```python
BAND_BG = "#171512"    # was MAROON — top/bottom band fill; rename every use site
STAMP_RED = "#B93511"
PAPER = "#F7F3EC"
AGED = "#EFE7D8"
INK = "#171512"
```

Rename every `MAROON` reference in the file (the two `d.rectangle(..., fill=MAROON)` calls) to `BAND_BG`. Leave `DISPLAY_FONTS` and `MONO_FONTS` as font-role lists (display headline vs. mono labels/date) and only prepend the bundled display font:

```python
_FONT_DIR = str(Path(__file__).resolve().parent.parent / "static" / "fonts")
DISPLAY_FONTS = [_FONT_DIR + "/PlayfairDisplay.ttf", *DISPLAY_FONTS]
```

`MONO_FONTS` is unchanged (still system Consolas/Courier/DejaVu Mono fallbacks) — it renders the "VOL. 1" subline, the postmark date, and the footer tagline, all of which stay monospace-styled, matching the site's IBM Plex Mono usage elsewhere.

`main.js` — poster tap-to-share (delegated, works on home/pay):

```js
  /* ---------- posters: tap to share ---------- */
  document.querySelectorAll(".poster[data-poster-id]").forEach(function (card) {
    card.addEventListener("click", function () {
      var id = card.dataset.posterId, caption = card.dataset.caption || "";
      var pngUrl = location.origin + "/posters/" + id + ".png";
      if (navigator.canShare && window.fetch) {
        fetch(pngUrl).then(function (r) { return r.blob(); }).then(function (blob) {
          var file = new File([blob], id + ".png", { type: "image/png" });
          if (navigator.canShare({ files: [file] })) {
            return navigator.share({ files: [file], text: caption });
          }
          return navigator.share({ text: caption, url: "https://janatakibaat.in" });
        }).catch(function () { /* user closed sheet */ });
      } else {
        navigator.clipboard && navigator.clipboard.writeText(caption);
        window.open(pngUrl, "_blank");
      }
    });
  });
```

Wipe the card cache so restyled cards regenerate: `rm -f app/static/cards/*.png`.

- [ ] **Step 5: Run — expect PASS. Open `/posters/cant-march.png` and one share card in the browser** — Playfair headline, no maroon.
- [ ] **Step 6: Commit** — `git add -A && git commit -m "feat: poster PNG renderer + web share; restyle share cards; bundle OFL fonts"`

---

### Task 11: Email restyle + sponsor receipt

**Files:**
- Modify: `app/templates/emails/_base.html`, `order_received.html`, `payment_confirmed.html`, `posted.html`
- Create: `app/templates/emails/sponsor_receipt.html`
- Modify: `scripts/smoke_test.py`

- [ ] **Step 1: Failing check** — extend the outbox section:

```python
    latest = max(mails, key=lambda p: p.stat().st_mtime).read_text(encoding="utf-8")
    check("emails restyled (no maroon)", "3D0808" not in latest and "C1121F" not in latest)
    check("sponsor receipt sent", any("receipt" in m.name for m in mails))
```

(The sponsor confirm in Task 8's checks already fires the receipt email into the outbox.)

- [ ] **Step 2: Run — expect FAIL** (`emails restyled`).

- [ ] **Step 3: Implement**

`_base.html` shell palette swap: body bg `#F7F3EC`; header band `#171512` with the masthead set in `Georgia, 'Times New Roman', serif` (email-safe letterpress stand-in), sub-line `#EFE7D8`; content card `#FBF8F2` with `1px solid #d9d2c4` border; buttons `background:#B93511; border:1px solid #171512`; footer text `#6E675C`. Apply the same button/accent swap inside the three message templates (`#C1121F`→`#B93511`, `#3D0808`→`#171512`, `#E9DDC4`→`#EFE7D8`, `Arial Black`→`Georgia`).

`sponsor_receipt.html`:

```html
{% from "emails/_base.html" import email_shell %}
{% call email_shell("Receipt — your sponsorship is in the Letters Fund.") %}
  <p>Namaste,</p>
  <p><strong>₹{{ s.amount }} received.</strong> You just sponsored
  {{ s.bundle_qty }} letter{{ 's' if s.bundle_qty > 1 }} to the Education
  Ministry for someone who couldn't spare the stamp.</p>
  <p>Your money sits in the public Letters Fund and leaves it only as
  postage — every paisa visible on the ledger under
  <span style="font-family:Courier New,monospace;">{{ s.public_code }}</span>.</p>
  <p>When a sponsored letter posts, it counts on the public counter like
  any other. Distance is not silence — and now, neither is a tight month.</p>
  <p>— Janata Ki Baat<br>
  <span style="font-size:13px;">From the students, for the students.</span></p>
{% endcall %}
```

- [ ] **Step 4: Run — expect PASS; open the newest files in `instance/outbox/`** in a browser.
- [ ] **Step 5: Commit** — `git add -A && git commit -m "redesign: emails in ink-letterpress palette + sponsor receipt"`

---

### Task 12: Remaining pages reskin (ledger, DIY, policies, admin, errors)

**Files:**
- Modify: `app/templates/ledger.html`, `diy.html`, `404.html`, `429.html`, `pages/*.html`, `admin/login.html`, `admin/queue.html`, `admin/order.html`, `app/static/css/style.css`

- [ ] **Step 1: Failing check** — the reskin's testable delta is the new Letters Fund totals card:

```python
    r = client.get("/ledger")
    check("ledger fund card", b"LETTERS FUND" in r.data)
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

`style.css`: restyle the old `.ledger-*`, `.admin-*`, `.faq`, `.form-grid/.field`, `.flash`, `.timeline`-leftovers, `.full-banner` blocks into tokens (hairlines, `--card` backgrounds, Playfair `.amt`, mono labels; `.flash-success` `#E4EAD9`, `.flash-error` `#F3DBD3` with `--verm-deep` border). `ledger.html`: totals order — In / Out / **LETTERS FUND** (label uppercase; value `tip+fund` sum) / Letters confirmed; note under the grid: *"The Letters Fund pays postage for can't-pay letters — entries tagged `fund`."* `diy.html`, policy pages, error pages: heading/kicker classes only (copy frozen). Admin templates: swap remaining inline maroon-era classes; sponsor tab from Task 8 gets the same table styling; keep everything utilitarian.

- [ ] **Step 4: Run — expect PASS; eyeball `/ledger`, `/admin` (logged in), `/about`.**
- [ ] **Step 5: Commit** — `git add -A && git commit -m "redesign: ledger fund card + reskin of remaining pages and admin"`

---

### Task 13: Final sweep — no-maroon grep, a11y, full run, launch notes

**Files:**
- Modify: `README.md`, `scripts/smoke_test.py` (final count), possibly stragglers found by grep

- [ ] **Step 1: Sweep**

```bash
grep -rniE "3D0808|6E1010|C1121F|A50F1B|Anton" app/ && echo "FOUND STRAGGLERS" || echo "clean"
```
Expected: `clean`. Fix any hits (including `app/services/pdf.py` INK constant is `#191111` — acceptable, not maroon; leave).

- [ ] **Step 2: Full smoke run**

```bash
rm -f instance/smoke_test.db && ./.venv/Scripts/python scripts/smoke_test.py
```
Expected: `ALL <N> CHECKS PASSED` with N ≥ 60. Then `./.venv/Scripts/python run.py` and manually verify at 1280px and 360px: home, write (signature + chips), pay (QR + share), status (thunk once), sponsor, ledger. Verify reduced-motion: DevTools → Rendering → emulate `prefers-reduced-motion` → no animations.

- [ ] **Step 3: README updates**

Update the repo-map section (new files: `_art.html`, `posters.py`, `sponsor` templates, `fonts/`), document `DAILY_CAP=0` semantics + `BATCH_PACE`, the batch-photo drop folder (`app/static/batches/*.jpg` → proof wall), and add to the launch checklist: "poster share test on a real Android phone" and "thunk + signature check on mobile Safari/Chrome".

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "redesign: final sweep — no maroon, a11y pass, README ops notes"
```

---

## Self-Review (performed at planning time)

- **Spec coverage:** §3 tokens→T1 · §4 art→T2 · §5.1→T1/T2 · §5.2+fuel/posters→T3 · §5.3→T5 · §5.4→T6 · §5.5→T7 · §5.6→T8/T9 · §5.7→T12 · §6→T3/T6/T7/T10 · §7→T3/T5/T7 · §8→T4 · §9→T4/T8/T9/T10 · §10→T1/T13 · §11 acceptance→T13. No gaps.
- **Type consistency:** `promised_post_date()` (T4) used in T4 admin confirm and T7 template via `order.promised_date`; `gen_public_code(prefix, model)` (T8) backwards-compatible with T-existing calls (defaults); `fund_balance()` defined T8, used T9; `_posters()` defined T3, used T6/T10; `Sponsorship.total` property satisfies `payments.upi_uri`.
- **Placeholder scan:** clean — every code step shows code or points at exact in-repo mockup sections.
