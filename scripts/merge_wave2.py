#!/usr/bin/env python3
"""
Merge Wave 2 enriched prospect CSVs into master-prospects.csv.
Run after enrich_csvs.py completes for the Wave 2 zones.

Wave 2 zones: fourth-ave-downtown, dove-mountain-marana, broadway-corridor
"""
import csv
from pathlib import Path

REPO = Path(__file__).parent.parent
MASTER = REPO / "data" / "master-prospects.csv"

WAVE2_ZONES = [
    "fourth-ave-downtown",
    "dove-mountain-marana",
    "broadway-corridor",
]

# Read master CSV header and existing place_ids (dedup check)
with open(MASTER, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    master_fields = list(reader.fieldnames or [])
    master_rows = list(reader)
    existing_ids = {r.get("place_id", "").strip() for r in master_rows if r.get("place_id", "").strip()}

print(f"Master CSV: {len(master_rows)} existing rows, {len(existing_ids)} unique place_ids")

# Collect Wave 2 rows from each zone CSV
new_rows = []
zone_counts = {}

for zone in WAVE2_ZONES:
    zone_csv = REPO / "prospects" / zone / f"{zone}-prospects.csv"
    if not zone_csv.exists():
        print(f"  WARNING: {zone_csv} not found — skipping")
        continue
    with open(zone_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        zone_rows = list(reader)

    added = 0
    for row in zone_rows:
        pid = row.get("place_id", "").strip()
        if pid and pid in existing_ids:
            continue  # already in master
        # Normalize row to master field list
        normed = {k: row.get(k, "") for k in master_fields}
        new_rows.append(normed)
        if pid:
            existing_ids.add(pid)
        added += 1
    zone_counts[zone] = added
    print(f"  {zone}: +{added} rows (of {len(zone_rows)} total)")

if not new_rows:
    print("No new rows to append — exiting.")
    exit(0)

# Append to master CSV
with open(MASTER, "a", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=master_fields, extrasaction="ignore")
    writer.writerows(new_rows)

total_new = len(new_rows)
new_master_total = len(master_rows) + total_new
print(f"\nMerge complete:")
for zone, count in zone_counts.items():
    print(f"  {zone}: +{count}")
print(f"  Total added: {total_new}")
print(f"  Master now: {new_master_total} rows")
