# dd-tucson-clientele

Tucson AZ prospect data and outreach documents for the Digital Disconnections sales pipeline.

**For the full sweep-to-send SOP, see [WORKFLOW.md](./WORKFLOW.md).**

## What This Repo Is For

This repository is the source of truth for all Tucson-area prospect research, outreach templates, and pipeline tracking. Each neighborhood has its own folder under `prospects/` for per-business outreach documents and notes.

## Quick Start — Running a Sweep

```bash
# 1. Sweep a new zone (edit ZONES in places_sweep.py first)
python3 places_sweep.py

# 2. Filter national chains
python3 scripts/filter_chains.py

# 3. Enrich (registrar, platform, domain suggestions)
python3 enrich_csvs.py

# 4. Rebuild HTML viewer
python3 build_html.py
```

See [WORKFLOW.md](./WORKFLOW.md) for the full SOP, template selection guide, data schema, and scripts cheat sheet.

## Directory Structure

```
dd-tucson-clientele/
├── README.md
├── WORKFLOW.md                  <- full SOP
├── places_sweep.py              <- Google Places API sweep
├── enrich_csvs.py               <- registrar/platform/domain enrichment
├── build_html.py                <- HTML viewer generator
├── data/
│   ├── master-prospects.csv     <- consolidated prospect list
│   └── removed_chains.csv       <- chain filter audit log
├── prospects/
│   ├── catalina-foothills/
│   ├── oro-valley/
│   ├── tanque-verde-sabino/
│   ├── sam-hughes-university/
│   ├── casas-adobes/
│   ├── fourth-ave-downtown/
│   ├── dove-mountain-marana/
│   ├── broadway-corridor/
│   ├── rita-ranch-vail/
│   └── sahuarita-green-valley/
├── html/                        <- board-facing HTML viewer
│   ├── index.html
│   └── <neighborhood>.html
├── templates/
│   └── outreach-template.md
└── scripts/
    ├── chain_blocklist.txt      <- national chain patterns
    └── filter_chains.py         <- chain filter script
```

## master-prospects.csv Column Reference

| Column | Description |
|--------|-------------|
| `business_name` | Full display name |
| `address` | Street address |
| `phone` | Primary phone |
| `category` | Business type (restaurant, bar, salon, etc.) |
| `neighborhood` | Zone key matching folder name |
| `google_maps_url` | Google Maps link |
| `website_url` | Website URL or `none` |
| `quality_score` | 1-5 web presence quality (1=none, 5=excellent) |
| `platform` | Detected platform (Wix, WordPress, Squarespace, etc.) or `unknown` |
| `registrar` | Domain registrar from whois, or `n/a` for no-website rows |
| `est_monthly_cost` | Estimated current monthly web spend ($) |
| `pain_points` | Issue notes |
| `priority_rank` | Outreach priority (1=highest) |
| `outreach_doc_ready` | yes/no |
| `domain_suggestions` | Available .com candidates for no-website businesses |
| `rating` | Google review count (used for chain detection) |

## Related

- Paperclip issue: [DIG-788](/DIG/issues/DIG-788)
- Parent initiative: [DIG-744](/DIG/issues/DIG-744)
