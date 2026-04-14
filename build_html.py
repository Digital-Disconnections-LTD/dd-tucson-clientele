#!/usr/bin/env python3
"""Generate browsable HTML prospect viewer from master-prospects.csv."""

import csv
import os
import re
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(REPO, "data", "master-prospects.csv")
SHORTLIST_CSV_PATH = os.path.join(REPO, "data", "shortlist.csv")
HTML_DIR = os.path.join(REPO, "html")

DANGEROUS_KEYWORDS = [
    "hijacked", "gambling", "expired domain", "dead domain",
    "dead redirect", "expired SSL", "server down", "broken",
    "placeholder", "connection refused", "DNS failure", "DNS timeout",
    "security compromise", "ad tracking", "squatted",
]

SCORE_LABELS = {
    "1": "Critical",
    "2": "Urgent",
    "3": "Moderate",
    "4": "Low",
}

SCORE_COLORS = {
    "1": "#dc2626",
    "2": "#ea580c",
    "3": "#ca8a04",
    "4": "#65a30d",
}


def slugify(name):
    s = name.lower().strip()
    s = s.replace(".", "").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def is_dangerous(row):
    combined = f"{row['platform']} {row['pain_points']} {row['website_url']}".lower()
    return any(kw in combined for kw in DANGEROUS_KEYWORDS)


def domain_status(row):
    url = row["website_url"].strip()
    platform = row["platform"].strip().lower()
    pain = row["pain_points"].lower()
    if not url or url == "none":
        return "No website"
    if platform in ("hijacked",) or "hijacked" in pain or "gambling" in pain:
        return "Hijacked/Dangerous"
    if "expired domain" in platform or "dead domain" in platform or "dns" in pain:
        return "Domain dead"
    if "expired ssl" in platform or "expired ssl" in pain:
        return "Expired SSL"
    if "dead redirect" in platform or "redirect" in pain:
        return "Dead redirect"
    if platform in ("server down", "broken") or "connection refused" in pain or "401" in pain:
        return "Server down"
    if platform == "placeholder" or "placeholder" in pain:
        return "Placeholder"
    if "squatted" in pain or "squatted" in url:
        return "Squatted"
    if url and url != "none":
        return "Active"
    return "Unknown"


CSS = """
:root {
    --bg: #0f172a;
    --surface: #1e293b;
    --surface-hover: #334155;
    --border: #334155;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --accent: #60a5fa;
    --score-1: #dc2626;
    --score-2: #ea580c;
    --score-3: #ca8a04;
    --score-4: #65a30d;
    --danger-bg: #451a1a;
    --danger-border: #991b1b;
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
}

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 0.25rem; }

.subtitle { color: var(--text-muted); margin-bottom: 2rem; font-size: 0.95rem; }
.back-link { display: inline-block; margin-bottom: 1.5rem; font-size: 0.9rem; }

.summary-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    text-align: center;
}

.summary-card .number { font-size: 2rem; font-weight: 700; line-height: 1.2; }
.summary-card .label {
    font-size: 0.8rem; color: var(--text-muted);
    text-transform: uppercase; letter-spacing: 0.05em;
}

.hood-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 1rem;
    margin-bottom: 2rem;
}

.hood-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    transition: background 0.15s;
}
.hood-card:hover { background: var(--surface-hover); }
.hood-card h2 { font-size: 1.15rem; margin-bottom: 0.5rem; }
.hood-card h2 a { color: var(--text); }
.hood-card h2 a:hover { color: var(--accent); }

.hood-stats { display: flex; gap: 0.5rem; flex-wrap: wrap; }

.badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
}

.badge-score-1 { background: rgba(220,38,38,0.2); color: #fca5a5; }
.badge-score-2 { background: rgba(234,88,12,0.2); color: #fdba74; }
.badge-score-3 { background: rgba(202,138,4,0.2); color: #fde047; }
.badge-score-4 { background: rgba(101,163,13,0.2); color: #bef264; }

.table-wrap {
    overflow-x: auto;
    margin-bottom: 2rem;
    border-radius: 8px;
    border: 1px solid var(--border);
}

table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }

th {
    background: var(--surface);
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    position: sticky;
    top: 0;
    white-space: nowrap;
}

td {
    padding: 0.75rem 1rem;
    border-top: 1px solid var(--border);
    vertical-align: top;
}

tr:hover td { background: var(--surface-hover); }

tr.score-1 td { border-left: 3px solid var(--score-1); }
tr.score-2 td { border-left: 3px solid var(--score-2); }
tr.score-1 td:first-child, tr.score-2 td:first-child { padding-left: calc(1rem - 3px); }

tr.dangerous td { background: var(--danger-bg); }
tr.dangerous:hover td { background: #5c2121; }

.score-dot {
    display: inline-block;
    width: 10px; height: 10px;
    border-radius: 50%;
    margin-right: 0.35rem;
    vertical-align: middle;
}

.domain-tag {
    display: inline-block;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
}

.domain-none { background: rgba(148,163,184,0.2); color: #94a3b8; }
.domain-active { background: rgba(101,163,13,0.2); color: #bef264; }
.domain-danger { background: rgba(220,38,38,0.3); color: #fca5a5; border: 1px solid var(--danger-border); }
.domain-warn { background: rgba(234,88,12,0.2); color: #fdba74; }

.legend {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 2rem;
}

.legend h3 {
    font-size: 0.9rem;
    margin-bottom: 0.75rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.legend-items {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    gap: 0.5rem;
}

.legend-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; }

.pain-text { font-size: 0.8rem; color: var(--text-muted); max-width: 350px; }

footer {
    margin-top: 3rem; padding-top: 1rem;
    border-top: 1px solid var(--border);
    font-size: 0.8rem; color: var(--text-muted); text-align: center;
}

@media (max-width: 640px) {
    body { padding: 1rem; }
    h1 { font-size: 1.35rem; }
    .summary-grid { grid-template-columns: repeat(2, 1fr); }
    .hood-list { grid-template-columns: 1fr; }
    td, th { padding: 0.5rem; font-size: 0.8rem; }
    .pain-text { max-width: 200px; }
}
"""


def html_escape(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def display_name(slug):
    special = {
        "catalina-foothills": "Catalina Foothills",
        "oro-valley": "Oro Valley",
        "tanque-verde-sabino": "Tanque Verde / Sabino Canyon",
        "sam-hughes-university": "Sam Hughes / University",
        "casas-adobes": "Casas Adobes",
        "fourth-ave-downtown": "Fourth Ave / Downtown",
        "dove-mountain-marana": "Dove Mountain / Marana",
        "broadway-corridor": "Broadway Corridor",
        "rita-ranch-vail": "Rita Ranch / Vail",
        "sahuarita-green-valley": "Sahuarita / Green Valley",
    }
    if slug in special:
        return special[slug]
    return slug.replace("-", " ").title()


def score_dot_html(score):
    color = SCORE_COLORS.get(score, "#666")
    label = SCORE_LABELS.get(score, score)
    return f'<span class="score-dot" style="background:{color}" title="Score {score}: {label}"></span>{score}'


def domain_tag_html(row):
    status = domain_status(row)
    if status == "No website":
        cls = "domain-none"
    elif status == "Active":
        cls = "domain-active"
    elif status in ("Hijacked/Dangerous", "Squatted"):
        cls = "domain-danger"
    else:
        cls = "domain-warn"
    return f'<span class="domain-tag {cls}">{html_escape(status)}</span>'


def render_index(neighborhoods, all_rows):
    total = len(all_rows)
    scores = Counter(r["quality_score"] for r in all_rows)

    hood_cards = []
    for slug in sorted(neighborhoods.keys(), key=lambda s: display_name(s)):
        rows = neighborhoods[slug]
        name = display_name(slug)
        sc = Counter(r["quality_score"] for r in rows)
        badges = "".join(
            f'<span class="badge badge-score-{s}">{sc.get(s, 0)} score-{s}</span>'
            for s in ("1", "2", "3", "4") if sc.get(s, 0) > 0
        )
        fname = slugify(slug)
        hood_cards.append(f"""
        <div class="hood-card">
            <h2><a href="{fname}.html">{html_escape(name)}</a></h2>
            <p style="color:var(--text-muted);font-size:0.9rem;margin-bottom:0.5rem">{len(rows)} prospects</p>
            <div class="hood-stats">{badges}</div>
        </div>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Tucson Prospect Viewer — Digital Disconnections</title>
<style>{CSS}</style>
</head>
<body>

<h1>Tucson Prospect Viewer</h1>
<p class="subtitle">Digital Disconnections — {total} prospects across {len(neighborhoods)} neighborhoods</p>

<div class="summary-grid">
    <div class="summary-card">
        <div class="number">{total}</div>
        <div class="label">Total Prospects</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-1)">{scores.get("1", 0)}</div>
        <div class="label">Score 1 (Critical)</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-2)">{scores.get("2", 0)}</div>
        <div class="label">Score 2 (Urgent)</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-3)">{scores.get("3", 0)}</div>
        <div class="label">Score 3 (Moderate)</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-4)">{scores.get("4", 0)}</div>
        <div class="label">Score 4 (Low)</div>
    </div>
    <div class="summary-card">
        <div class="number">{len(neighborhoods)}</div>
        <div class="label">Neighborhoods</div>
    </div>
</div>

<div style="margin-bottom:2rem">
    <a href="shortlist.html" style="display:inline-flex;align-items:center;gap:0.5rem;background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.3);border-radius:8px;padding:0.75rem 1.25rem;color:var(--accent);font-weight:600;text-decoration:none;">
        &#9733; View Outreach Shortlist &rarr;
    </a>
    <span style="margin-left:1rem;color:var(--text-muted);font-size:0.9rem">Top 50 prospects scored &amp; ranked for outreach</span>
</div>

<div class="legend">
    <h3>Scoring Rubric</h3>
    <div class="legend-items">
        <div class="legend-item"><span class="score-dot" style="background:var(--score-1)"></span> <strong>Score 1 — Critical:</strong> No website, hijacked domain, or dangerous redirect</div>
        <div class="legend-item"><span class="score-dot" style="background:var(--score-2)"></span> <strong>Score 2 — Urgent:</strong> Expired SSL, dead domain, server down, or broken site</div>
        <div class="legend-item"><span class="score-dot" style="background:var(--score-3)"></span> <strong>Score 3 — Moderate:</strong> Outdated site, neglected content, or visibly stale</div>
        <div class="legend-item"><span class="score-dot" style="background:var(--score-4)"></span> <strong>Score 4 — Low:</strong> Generic template or minor issues but functional</div>
    </div>
</div>

<h2 style="margin-bottom:1rem">Neighborhoods</h2>
<div class="hood-list">
{"".join(hood_cards)}
</div>

<footer>Generated from master-prospects.csv &middot; Digital Disconnections Ltd</footer>
</body>
</html>"""


def render_neighborhood(slug, rows):
    name = display_name(slug)
    def sort_key(r):
        s = r["quality_score"].strip()
        p = (r.get("priority_rank") or "").strip()
        return (int(s) if s.isdigit() else 99, int(p) if p.isdigit() else 999)
    rows_sorted = sorted(rows, key=sort_key)

    scores = Counter(r["quality_score"] for r in rows)

    table_rows = []
    for r in rows_sorted:
        score = r["quality_score"]
        dangerous = is_dangerous(r)
        cls_parts = []
        if score in ("1", "2"):
            cls_parts.append(f"score-{score}")
        if dangerous:
            cls_parts.append("dangerous")
        cls = f' class="{" ".join(cls_parts)}"' if cls_parts else ""

        url = r["website_url"].strip()
        if url and url != "none":
            url_display = f'<a href="{html_escape(url)}" target="_blank" rel="noopener">{html_escape(url[:40])}</a>'
        else:
            url_display = '<span style="color:var(--text-muted)">—</span>'

        platform = r["platform"].strip() or "—"
        pain = r["pain_points"].strip()

        table_rows.append(f"""
            <tr{cls}>
                <td><strong>{html_escape(r["business_name"])}</strong></td>
                <td>{html_escape(r["category"])}</td>
                <td>{score_dot_html(score)}</td>
                <td class="pain-text">{html_escape(pain)}</td>
                <td>{html_escape(platform)}</td>
                <td>{domain_tag_html(r)}</td>
            </tr>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html_escape(name)} — Tucson Prospect Viewer</title>
<style>{CSS}</style>
</head>
<body>

<a href="index.html" class="back-link">&larr; All Neighborhoods</a>

<h1>{html_escape(name)}</h1>
<p class="subtitle">{len(rows)} prospects</p>

<div class="summary-grid">
    <div class="summary-card">
        <div class="number">{len(rows)}</div>
        <div class="label">Total</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-1)">{scores.get("1", 0)}</div>
        <div class="label">Critical</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-2)">{scores.get("2", 0)}</div>
        <div class="label">Urgent</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-3)">{scores.get("3", 0)}</div>
        <div class="label">Moderate</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:var(--score-4)">{scores.get("4", 0)}</div>
        <div class="label">Low</div>
    </div>
</div>

<div class="legend">
    <h3>Scoring Rubric</h3>
    <div class="legend-items">
        <div class="legend-item"><span class="score-dot" style="background:var(--score-1)"></span> <strong>1 Critical:</strong> No site, hijacked, or dangerous</div>
        <div class="legend-item"><span class="score-dot" style="background:var(--score-2)"></span> <strong>2 Urgent:</strong> Expired SSL, dead domain, broken</div>
        <div class="legend-item"><span class="score-dot" style="background:var(--score-3)"></span> <strong>3 Moderate:</strong> Outdated, neglected content</div>
        <div class="legend-item"><span class="score-dot" style="background:var(--score-4)"></span> <strong>4 Low:</strong> Generic template, minor issues</div>
    </div>
</div>

<div class="table-wrap">
<table>
<thead>
    <tr>
        <th>Business Name</th>
        <th>Category</th>
        <th>Score</th>
        <th>Signal / Notes</th>
        <th>Platform</th>
        <th>Domain Status</th>
    </tr>
</thead>
<tbody>
{"".join(table_rows)}
</tbody>
</table>
</div>

<a href="index.html" class="back-link">&larr; All Neighborhoods</a>

<footer>Generated from master-prospects.csv &middot; Digital Disconnections Ltd</footer>
</body>
</html>"""


TIER_COLORS = {
    "1": "#dc2626",
    "2": "#ea580c",
    "3": "#ca8a04",
}

TIER_LABELS = {
    "1": "No Website",
    "2": "Weak Platform",
    "3": "WP / Squarespace",
}


def render_shortlist(shortlist_rows):
    total = len(shortlist_rows)
    tier_counts = Counter(r["tier"] for r in shortlist_rows)

    zone_display = {
        "catalina-foothills": "Catalina Foothills",
        "oro-valley": "Oro Valley",
        "tanque-verde-sabino": "Tanque Verde / Sabino",
        "casas-adobes": "Casas Adobes",
        "sam-hughes-university": "Sam Hughes / University",
    }

    table_rows = []
    for rank, r in enumerate(shortlist_rows, 1):
        tier = r.get("tier", "")
        tier_color = TIER_COLORS.get(tier, "#666")
        tier_label = TIER_LABELS.get(tier, f"Tier {tier}")
        zone = zone_display.get(r.get("zone", ""), r.get("zone", ""))
        score = r.get("score", "")
        rating = r.get("google_rating", "").strip()
        reviews = r.get("review_count", "").strip()
        domain = r.get("domain_suggestion", "").strip()
        maps_url = r.get("google_maps_url", "").strip()
        name = r.get("business_name", "")
        category = r.get("category", "").replace("_", " ")
        platform = r.get("platform", "none").strip()
        rationale = r.get("rationale", "")

        name_cell = (
            f'<a href="{html_escape(maps_url)}" target="_blank" rel="noopener">'
            f'<strong>{html_escape(name)}</strong></a>'
            if maps_url else f'<strong>{html_escape(name)}</strong>'
        )

        domain_cell = (
            f'<span style="font-family:monospace;font-size:0.8rem;color:var(--accent)">'
            f'{html_escape(domain)}</span>'
            if domain else '<span style="color:var(--text-muted)">—</span>'
        )

        tier_badge = (
            f'<span style="display:inline-block;padding:0.1rem 0.45rem;border-radius:3px;'
            f'font-size:0.75rem;font-weight:700;background:rgba(255,255,255,0.08);'
            f'color:{tier_color};border:1px solid {tier_color}40">'
            f'T{tier} {tier_label}</span>'
        )

        rating_str = f"{rating}★" if rating else "—"
        review_str = reviews if reviews else "—"

        table_rows.append(f"""
            <tr>
                <td style="color:var(--text-muted);width:2.5rem;text-align:center">{rank}</td>
                <td>{name_cell}<br><span style="font-size:0.8rem;color:var(--text-muted)">{html_escape(category)}</span></td>
                <td>{tier_badge}</td>
                <td style="text-align:center;font-weight:600;color:{tier_color}">{html_escape(score)}</td>
                <td>{html_escape(zone)}</td>
                <td style="font-size:0.85rem;color:var(--text-muted)">{html_escape(platform)}</td>
                <td>{domain_cell}</td>
                <td style="text-align:center">{html_escape(rating_str)}</td>
                <td style="text-align:center">{html_escape(review_str)}</td>
                <td class="pain-text" style="font-size:0.8rem;color:var(--text-muted)">{html_escape(rationale)}</td>
            </tr>""")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outreach Shortlist — Tucson Prospects</title>
<style>{CSS}</style>
</head>
<body>

<a href="index.html" class="back-link">&larr; All Neighborhoods</a>

<h1>&#9733; Outreach Shortlist</h1>
<p class="subtitle">Top {total} Tucson prospects scored &amp; ranked for outreach — Wave 1</p>

<div class="summary-grid">
    <div class="summary-card">
        <div class="number">{total}</div>
        <div class="label">Total Selected</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:{TIER_COLORS['1']}">{tier_counts.get('1', 0)}</div>
        <div class="label">Tier 1 — No Website</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:{TIER_COLORS['2']}">{tier_counts.get('2', 0)}</div>
        <div class="label">Tier 2 — Weak Platform</div>
    </div>
    <div class="summary-card">
        <div class="number" style="color:{TIER_COLORS['3']}">{tier_counts.get('3', 0)}</div>
        <div class="label">Tier 3 — WP / Squarespace</div>
    </div>
</div>

<div class="legend">
    <h3>Tier Guide</h3>
    <div class="legend-items">
        <div class="legend-item">
            <span class="score-dot" style="background:{TIER_COLORS['1']}"></span>
            <strong>Tier 1 — No Website:</strong> Business has zero web presence. Lead with domain suggestion. Highest conversion potential.
        </div>
        <div class="legend-item">
            <span class="score-dot" style="background:{TIER_COLORS['2']}"></span>
            <strong>Tier 2 — Weak Platform:</strong> On Wix, Weebly, or other template builders. Pitch professional redesign + cost comparison.
        </div>
        <div class="legend-item">
            <span class="score-dot" style="background:{TIER_COLORS['3']}"></span>
            <strong>Tier 3 — WP / Squarespace:</strong> Has a capable platform but outdated execution. Pitch visual refresh or full redesign.
        </div>
    </div>
</div>

<div class="table-wrap">
<table>
<thead>
    <tr>
        <th>#</th>
        <th>Business</th>
        <th>Tier</th>
        <th>Score</th>
        <th>Zone</th>
        <th>Platform</th>
        <th>Domain Suggestion</th>
        <th>Rating</th>
        <th>Reviews</th>
        <th>Rationale</th>
    </tr>
</thead>
<tbody>
{"".join(table_rows)}
</tbody>
</table>
</div>

<a href="index.html" class="back-link">&larr; All Neighborhoods</a>

<footer>Generated from data/shortlist.csv &middot; Digital Disconnections Ltd</footer>
</body>
</html>"""


def main():
    os.makedirs(HTML_DIR, exist_ok=True)

    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    neighborhoods = defaultdict(list)
    for row in all_rows:
        hood = row["neighborhood"].strip()
        if hood:
            neighborhoods[hood].append(row)

    slug_map = {}
    for hood in neighborhoods:
        slug_map[hood] = slugify(hood)

    index_by_slug = {}
    for hood, rows in neighborhoods.items():
        s = slug_map[hood]
        if s in index_by_slug:
            index_by_slug[s].extend(rows)
        else:
            index_by_slug[s] = list(rows)

    with open(os.path.join(HTML_DIR, "index.html"), "w") as f:
        f.write(render_index(index_by_slug, all_rows))
    print(f"  index.html ({len(all_rows)} total prospects)")

    for slug, rows in sorted(index_by_slug.items()):
        fname = f"{slug}.html"
        with open(os.path.join(HTML_DIR, fname), "w") as f:
            f.write(render_neighborhood(slug, rows))
        print(f"  {fname} ({len(rows)} prospects)")

    # Generate shortlist view if shortlist CSV exists
    if os.path.exists(SHORTLIST_CSV_PATH):
        with open(SHORTLIST_CSV_PATH, newline="") as f:
            reader = csv.DictReader(f)
            shortlist_rows = list(reader)
        with open(os.path.join(HTML_DIR, "shortlist.html"), "w") as f:
            f.write(render_shortlist(shortlist_rows))
        print(f"  shortlist.html ({len(shortlist_rows)} prospects)")

    print(f"\nDone — {len(index_by_slug) + 2} files in html/")


if __name__ == "__main__":
    main()
