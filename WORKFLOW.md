# City Prospect Sweep — Tucson AZ Workflow

Standard operating procedure for researching Tucson-area neighborhoods, enriching the data, filtering chains, and preparing prospects for board review and outreach.

---

## Phase 1 — Prerequisites

Before starting a new sweep zone:

- **Google Places API key** — stored in `places_sweep.py`. Required for the Places API sweep (Phase 3).
- **`whois` installed** — required for registrar/domain enrichment (Phase 5). `apt install whois` on Debian/Ubuntu.
- **`curl` available** — required for platform fingerprinting (Phase 5).
- **Repo cloned** — `git clone https://github.com/Digital-Disconnections-LTD/dd-tucson-clientele.git`
- **Python 3.9+** — all scripts are stdlib-only except `places_sweep.py` which uses `urllib`.

---

## Phase 2 — Neighborhood Planning

**Zone grouping rules:**
- Group geographically adjacent neighborhoods together.
- Aim for 15-30 prospects per zone for the initial sweep pass.
- Use a ~4-5 km radius for dense urban areas; up to 6 km for suburban/rural corridors.
- Name folders with lowercase-hyphenated zone keys: `catalina-foothills`.

**Priority order (affluent-first):**
1. Catalina Foothills (Wave 1)
2. Oro Valley (Wave 1)
3. Tanque Verde / Sabino Canyon (Wave 1)
4. Sam Hughes / University (Wave 1)
5. Casas Adobes (Wave 1)
6. Fourth Ave / Downtown (Wave 2)
7. Dove Mountain / Marana (Wave 2)
8. Broadway Corridor (Wave 2)
9. Rita Ranch / Vail (Wave 3)
10. Sahuarita / Green Valley (Wave 3)

---

## Phase 3 — Places API Sweep

**Script:** `python3 places_sweep.py`

Edit `ZONES` at the top of the script to add new neighborhood targets:

```python
ZONES = [
    ("zone-key", "folder-name", LAT, LNG, RADIUS_METERS),
]
```

**Business types to include** (Google Places `includedTypes`):
- Food: `restaurant`, `bar`, `cafe`, `bakery`, `meal_delivery`, `meal_takeaway`
- Beauty: `hair_salon`, `beauty_salon`, `nail_salon`, `spa`, `barber_shop`
- Health: `dentist`, `doctor`, `physiotherapist`, `optician`
- Retail: `clothing_store`, `jewelry_store`, `florist`, `book_store`, `gift_shop`
- Auto: `car_repair`, `car_wash` (local independent only — chains filtered in Phase 4)
- Other: `laundry`, `dry_cleaning`, `locksmith`, `tailor`, `pet_store`, `general_contractor`

**Quality scoring guide:**
- `1` — no website at all
- `2` — website exists but quality unknown (to be refined)
- `3` — website clearly outdated, mobile-unfriendly, or on a free subdomain
- `4` — decent site but overpriced platform or clear pain points
- `5` — good site, low priority

---

## Phase 4 — Chain Filtering

**Script:** `python3 scripts/filter_chains.py`

Run immediately after every Places API sweep before committing:

```bash
python3 scripts/filter_chains.py
```

**Blocklist:** `scripts/chain_blocklist.txt` — patterns covering fast food, national retail, hair chains, fitness, auto services, banking, etc.

**1,000+ review flag:** Any business with `rating` >= 1000 reviews should be manually reviewed before keeping. Most are chains; some are beloved locals.

**AZ-specific chains to watch for:**
- Eegee's (Tucson-only chain, 25+ locations — filter)
- Fry's Food (Kroger subsidiary — already in blocklist via Kroger)
- Circle K (AZ-headquartered — already in blocklist)
- Native Grill & Wings (AZ franchise chain — add if volume warrants)
- Oregano's Pizza Bistro (AZ regional chain — add if volume warrants)

---

## Phase 5 — Basic Enrichment

**Script:** `python3 enrich_csvs.py`

Adds columns: `registrar`, `platform`, `domain_suggestions`.

The enrichment script auto-discovers all `*-prospects.csv` files under `prospects/`.

**Domain suggestions** for no-website businesses check:
- `businessname.com`
- `businessnametucson.com`
- `businessnameaz.com`
- `businessnamearizona.com`

---

## Phase 6 — Deep Enrichment

Adds to each row:
- **`owner_name`** — AZ Corporation Commission filings + website About pages
- **`email`** — website contact pages + WHOIS registrant email
- **`facebook_url`** / **`instagram_url`** — from Places API / site footers
- **`mobile_friendly`** — viewport meta tag check
- **`delivery_platforms`** — DoorDash/GrubHub/UberEats flags

---

## Phase 7 — HTML Viewer

**Script:** `python3 build_html.py`

Regenerates `html/` from `data/master-prospects.csv`. Run after any data update.

---

## Phase 8 — Board Review Gate

**No sends until the board has reviewed GitHub and approved.**

---

## Phase 9 — Template Selection

Five outreach templates in `templates/`:

| Template | Use case |
|----------|----------|
| **A** — No website | Business with no web presence at all. Lead with domain suggestion. |
| **B** — Outdated site | Site exists but is visually old/broken. Show a before/after concept. |
| **C** — Wrong platform | On GoDaddy/Wix, paying too much. Lead with cost comparison. |
| **D** — Mobile only | Site works on desktop but broken on mobile. Screenshot proof. |
| **E** — High-value local | Well-known local institution. Soft pitch focused on reputation. |

---

## Scripts Cheat Sheet

```bash
# 1. Run a Places API sweep for new zones
python3 places_sweep.py

# 2. Filter national chains
python3 scripts/filter_chains.py

# 3. Enrich all CSVs
python3 enrich_csvs.py

# 4. Rebuild HTML viewer
python3 build_html.py

# 5. Add a new chain to the blocklist, then re-filter
echo "NewChainName" >> scripts/chain_blocklist.txt
python3 scripts/filter_chains.py
```

---

## Data Schema Reference

Full column set for `master-prospects.csv` and all neighborhood CSVs:

| Column | Type | Description |
|--------|------|-------------|
| `business_name` | string | Full display name |
| `address` | string | Street address |
| `phone` | string | Primary phone |
| `category` | string | Business type |
| `neighborhood` | string | Zone key matching folder name |
| `google_maps_url` | string | Google Maps link |
| `website_url` | string | Website URL or `none` |
| `quality_score` | int 1-5 | Web presence quality |
| `platform` | string | Detected platform or `unknown` |
| `registrar` | string | Domain registrar or `n/a` |
| `est_monthly_cost` | int | Estimated monthly web spend ($) |
| `pain_points` | string | Issue notes |
| `priority_rank` | int | Outreach priority (1=highest) |
| `outreach_doc_ready` | yes/no | Outreach doc prepared |
| `domain_suggestions` | string | Available .com candidates |
| `rating` | int | Google review count |
