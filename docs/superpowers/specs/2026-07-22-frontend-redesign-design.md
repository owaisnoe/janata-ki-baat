# Janata Ki Baat — Front-End Redesign: "Ink & Letterpress"

**Date:** 2026-07-22 · **Status:** approved in brainstorm (visual companion, mockups v1–v5)
**Reference mockup (approved):** `assets/2026-07-22-homepage-mockup-v5.html` — open in a browser; it is the visual source of truth for tokens, spacing, and section order.

## 1. Goal & non-goals

**Goal:** replace the CJP-adjacent maroon zine-brutalist front end with an elegant, smooth, personal **Ink & Letterpress** identity — warm paper, near-black ink, one vermilion accent — while keeping the postal soul (stamps, postmarks, proof) and the Mann-Ki-Baat-inversion copy engine. Add four product features: a spread-the-word poster system, a real Sponsor-a-Letter flow, Zomato-style tip chips, and uncapped intake with an honest posting-date promise.

**Non-goals:** no JS framework (vanilla JS + Jinja stays), no Hindi phase, no Razorpay swap, no change to the formal letter PDF (already serif — now matches the site), admin gets a token reskin only, no CMS.

## 2. Locked decisions (from the brainstorm)

| Decision | Choice |
|---|---|
| Direction | **B — Ink & Letterpress** (chosen over Inland Letter and Indigo & Clay) |
| Hero slogan | **"Every month, it's Mann Ki Baat. This month, it's Janata Ki Baat."** — quiet italic first line, 900-weight second line with hand-drawn vermilion underline |
| Shed | The maroon palette (CJP's colour). Newspaper conceits and satire register **stay**, executed elegantly |
| Masthead line | **"✦ FROM THE STUDENTS · FOR THE STUDENTS ✦"** (disclaimer stays verbatim in footer — legally load-bearing) |
| Header | Broadsheet ears (डाक pillar postbox left, NEW DELHI 110 001 postmark right), envelope ornament rule, **tricolour postal stripe** top edge (saffron+green dashes; never an actual flag, no chakra) |
| Graphics | **A+B+C:** engraved line art + vermilion hand-strokes/Caveat ink + duotone real proof photos. (D minimal-only rejected) |
| Personal layer | All four: ink signature, letter identity, name/city-aware copy, delight moments |
| Capacity | **Truly uncapped** (user decision; elastic-queue recommendation declined). Honest dynamic ETA shown at checkout; scarcity UI removed |
| Tips | Zomato-style one-tap chips, not a slider |
| News band | **Live news desk**: LIVE badge + updated-at stamp + drifting newswire ticker of dated, sourced headlines (hand-curated `fuel.json`; "live" is presentation — the trust rule stays *sourced, never rumour*) |

## 3. Design tokens (`style.css` `:root` rewrite)

```css
--paper: #F7F3EC;      /* page bg */
--paper-deep: #EFE7D8; /* plates, slogan-ticker bg */
--card: #FBF8F2;       /* tier cards, posters, envelope */
--ink: #171512;        /* text, dark bands */
--ink-soft: #2A2622;   /* body/secondary text — NOT stone (v2 feedback: too muted) */
--verm: #E2401B;       /* accent: large text ≥24px, strokes, dots only */
--verm-deep: #B93511;  /* small text, tags, borders — contrast-safe on paper */
--stone: #6E675C;      /* true fine print only */
--hair: rgba(23,21,18,.18);   /* hairline rules replace all 3px brutalist borders */
--saffron: #E07C1F; --green: #2E7D32;  /* tricolour stripe ONLY */
```

**Type:** Playfair Display (600 italic / 800 / 900) display · Inter (400–700) UI/body · IBM Plex Mono (400–600) labels, codes, tickers · **Caveat 600** — human ink only (addresses, signatures, poster annotations); never for UI chrome.
**Texture:** SVG turbulence grain overlay, opacity .3, `pointer-events:none`.
**Geometry:** 3px radius, hairline borders, soft shadows (`0 18px 50px rgba(23,21,18,.15)`). No offset hard shadows anywhere.
**Motion:** 150–250ms ease; hover lift 2–4px; all animation gated by `prefers-reduced-motion`.

## 4. Graphic language (three layers)

1. **Engraved line art** (inline SVG, stroke 1.2–1.6 ink, vermilion sub-accents): envelope, stamp (dashed perforation), postmark, डाक pillar postbox, mailbag, nib, check-circle, wax-seal circle, cancellation waves, Shastri Bhawan façade (status milestone). Built once as a small partial library (`templates/_art.html` macros).
2. **Hand strokes** (SVG paths, vermilion, round caps): hero underline, flourish rules, margin arrows. Plus Caveat for anything "written by a hand".
3. **Duotone proof photos:** CSS recipe `filter: grayscale(1) contrast(1.05)` under a vermilion-to-transparent gradient overlay; used on the home proof wall, status page proof, and posters. Pre-launch placeholder: styled envelope compositions (as mocked); swaps to real batch photos from day 1 of ops.

## 5. Page specs

### 5.1 Base (all pages)
Tricolour stripe → masthead (ears grid, hides <760px) → envelope ornament rule → mono nav → slogan ticker (paper-deep, 55s drift): counter + permit line + distance line + "POSTED · PHOTOGRAPHED · TRACKED". Footer: double rule, unchanged disclaimer, "SATIRE IN THE MARGINS · DEAD SERIOUS IN THE MAIL" in verm-deep mono.

### 5.2 Home (order as in approved mockup v5)
1. **Hero:** slogan + sub + vermilion CTA `Post my letter →` + ghost `Free DIY kit`; Playfair stat row (letters count — JS count-up once on view · ₹59 · "2 days to the mailbag"); tilted envelope artwork (stamp, postmark, Caveat address, JKB code).
2. **Live news desk** (dark, vermilion border-block): deskhead row — pulsing LIVE badge, "TODAY'S FUEL — SOURCED, NOT RUMOURED", `UPDATED {date} · {time} IST` from `fuel.json`; below, **newswire ticker** (48s drift, pause on hover): `{DATE} {headline → source url} {SOURCE}` items.
3. **Manifesto plate** (paper-deep, double inset rule): premise copy, centered Playfair.
4. **How it works:** 3 steps, engraved icons, hairline left rules.
5. **Tiers:** 3 cards (Speed Post vermilion-bordered "MOST PROOF", ePost, DIY), tags, hover lift.
6. **Proof wall** (dark band): duotone batch shots + `BATCH #N · {count} LETTERS` captions; note line + ledger link.
7. **Spread the word:** 3 tap-to-share posters (see §6).
8. **Sponsor band:** wax-seal SVG + fund pitch + sponsored count + CTA → `/sponsor`.
**Removed:** slots-left counter, mailbag-full banner, waitlist form (endpoint stays dormant).

### 5.3 Write
Two-pane layout kept. Template picker as three letterhead cards with engraved seals (nib = NEET accountability, lamp = solidarity, house = family cost). **Tip chips:** `₹0 no chai` · `₹10 cutting chai` · `₹20 chai + Parle-G` · `₹50 full tiffin` · `custom` (hidden number input) — copy notes every rupee lands in the public Letters Fund. Under the CTA, the honest queue line: *"In today's mailbag — posts by {promised_date}"*. **Live preview:** as the name is typed it renders in Caveat in the signature slot; the city fills a personal postmark SVG ("{CITY} · 2026") beside the form header. Preview-exact-PDF button unchanged.

### 5.4 Pay
QR inside a perforated stamp frame; amount in Playfair 900; order code as a mono booking slip; UTR form. **Share moment #2:** one poster card — *"Your letter is being matched. Tell one person while you wait."*

### 5.5 Status
Ownership header: **"Letter #1,248 — {name}'s letter to the Education Ministry"** + city postmark. Timeline becomes the **envelope's journey**: nib → stamp → mailbag → counter → Shastri Bhawan façade, engraved milestones, vermilion fill on completion. **Postmark thunk:** on first view at confirmed-or-later, the POSTED postmark stamps onto the page (scale+rotate keyframes, ~400ms; `sessionStorage` once-guard; reduced-motion → fade). Line: *"You are letter #1,248 of a mailbag that can't be scrolled past."* Proof photo duotone with photo-corner mounts. **Share moment #3:** personalised poster grid (restyled share cards + captions + Web Share). Expired/refunded banners restyled in tokens.

### 5.6 Sponsor (new page `/sponsor`)
Seal hero + fund explainer ("post someone else's anger"); bundle cards **1/3/5/10 letters = ₹59/₹177/₹295/₹590**; same UPI QR → UTR → admin-confirm flow; live fund balance + letters-sponsored count from the ledger; two FAQ lines (where money sits, how a free letter is claimed). Write page gains an *"I can't pay — post mine from the Letters Fund"* checkbox (creates a ₹0 order flagged `sponsored_request`; admin approves against fund balance).

### 5.7 Ledger, DIY, policies, errors, admin
Token/typography reskin only. Ledger totals in Playfair; tables keep structure. Admin stays utilitarian in new tokens. Refunds page copy updates per §8.

## 6. Spread-the-word system

- **Poster registry** (`app/data/posters.json`): id, headline, hand-line, theme (light/dark), caption. Launch set: "Can't march? Mail." · "Mann Ki Baat sunn li. Janata Ki Baat bhej di." · "{count} letters can't be scrolled past." (count baked at render).
- **Rendering:** HTML/CSS versions for on-page display; Pillow-rendered PNG per poster (1080×1350) served from `/static/posters/` for sharing. Pillow gets Playfair + Caveat TTFs bundled in `app/static/fonts/` (also fixes share-card fonts on cPanel).
- **Tap behaviour:** Web Share Level 2 with image file where supported (Android Chrome); else share url+caption; else copy caption + download PNG.
- **Placements:** home (3), pay (1), status (personalised grid via restyled `sharecard.py` — paper/ink/vermilion, Playfair + Caveat + postmark; maroon deleted).
- **Emails:** same palette swap; header set in the new masthead style.

## 7. Personalisation mechanics

| Touch | Where | How |
|---|---|---|
| Ink signature | write preview | JS mirrors name input into Caveat signature slot (textContent — no HTML injection) |
| City postmark | write + status | SVG partial with dynamic `{CITY}` text |
| Letter identity | status, emails, cards | "Letter #N", "{name}'s letter", serial in captions |
| Name-aware copy | status + confirmation email | "Asha, you are Letter #1,248" |
| Delight inventory | site-wide | postmark thunk (once), count-up counter (once), signature fade-in, newswire drift + LIVE pulse, hover lifts — all `prefers-reduced-motion`-gated |

## 8. Uncapped intake + honest promise

- `DAILY_CAP=0` ⇒ uncapped (new default in `.env.example`); `consume_slot()` short-circuits true; slots UI removed; waitlist dormant; cap re-enable is a config change (kept as the emergency brake).
- **Promised date:** `promised_date = next_working_day(today + ceil(queue_depth / batch_pace))` where `queue_depth` = paid-but-unposted orders and `batch_pace` = new config `BATCH_PACE` (default 50, operator-tunable). Shown on write, pay, status; stored per-order in new column `orders.promised_date` at confirmation.
- **Refund promise** (refunds page + emails): *"posted by the date shown when you ordered, or a full automatic refund"*. `sla_check.py` switches from flat 5-days to `posted_at > promised_date + 2 working days`.
- Risk note (acknowledged in brainstorm): solo throughput on a viral day; mitigations are the honest ETA, the sponsor/volunteer scale path, and the config brake.

## 9. Backend touches (the full list — nothing else changes)

1. `Order.promised_date` (date, nullable) + ETA util in `services/util.py`.
2. `Sponsorship` model: `id, public_code, email, bundle_qty, amount, status(pending_payment/utr_submitted/confirmed/expired), utr, timestamps` → ledger `fund` entry on confirm; admin queue tab; receipt email.
3. `Order.sponsored_request` (bool) for the can't-pay flow; admin approve action consumes fund on the ledger.
4. Routes: `/sponsor` (GET/POST + pay/UTR reuse), poster share endpoints.
5. `fuel.json` schema gains `source`, `updated_at`; poster registry file.
6. `sharecard.py` restyle + poster renderer; bundled TTFs.
7. Migration: pre-launch DB is disposable — recreate; document `ALTER TABLE` lines in README for safety.
8. Smoke test extended: uncapped create at cap=0, sponsor flow end-to-end, promised-date present, poster endpoints 200.

## 10. Accessibility & performance guardrails

Vermilion `#E2401B` only ≥24px or decorative; `#B93511` for small text (AA on paper); body text `--ink-soft`. Focus: 3px vermilion outline. Fonts: preconnect + `display=swap`; four families is the ceiling (Playfair Display + Inter + IBM Plex Mono + Caveat — Anton is removed). No frameworks; new JS ≈ few KB. Grain overlay non-interactive. Lighthouse a11y ≥ 90 on home/write/status. All pages usable at 360px (v2 feedback: mobile is first-class — most traffic arrives from Instagram).

## 11. Acceptance criteria

- Zero maroon anywhere: site, share cards, posters, emails, QR page.
- Home matches mockup v5 section order and tokens at 1280px and 360px.
- Write shows live Caveat signature, tip chips, and the posts-by date; pay shows stamp-frame QR + share moment; status shows journey timeline, one-time thunk, personalised share grid.
- Sponsor flow completable end-to-end (bundle → UPI → UTR → admin confirm → ledger fund entry → counter updates).
- Posters share image+caption on Android Chrome, degrade gracefully elsewhere.
- Extended smoke test green; `prefers-reduced-motion` verified.
