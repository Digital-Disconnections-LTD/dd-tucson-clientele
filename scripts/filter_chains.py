#!/usr/bin/env python3
"""
Filter national chain businesses out of all prospect CSVs.
Uses scripts/chain_blocklist.txt for matching (case-insensitive substring).

Usage:
    python3 scripts/filter_chains.py [--dry-run]

Reports removal counts per file and writes a removed_chains.csv log.
"""
import csv
import glob
import os
import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
BLOCKLIST_PATH = REPO_ROOT / 'scripts' / 'chain_blocklist.txt'
REMOVED_LOG_PATH = REPO_ROOT / 'data' / 'removed_chains.csv'

DRY_RUN = '--dry-run' in sys.argv

# FALSE POSITIVE EXCLUSIONS — names that match a chain keyword but are local businesses
# Add here when filter_chains.py removes a business you want to keep.
FALSE_POSITIVES = {
    "dana's dunkin' duds laundry",       # laundromat (not Dunkin') — matched by "Dunkin" keyword
    "national apartment laundries",       # local laundry service — matched by "national" in name
    "moe's lounge & grill",              # local Pittsburgh bar — matched by "Moe's" (Moe's Southwest Grill)
    "ross d. vaughan, dc",               # local chiropractor — matched by "Ross" if that entry exists
    "europe nails & spa (ross park mall)", # local salon — "Ross" appears in mall name, not chain name
    "threadbare cider tasting room & bottle shop at ross park mall",  # local cidery — same
}

def load_blocklist(path):
    patterns = []
    with open(path) as f:
        for line in f:
            # Strip inline comments (everything after the first unquoted #)
            line = line.split('#')[0].strip()
            if not line:
                continue
            # Use word-boundary anchors so short entries like "Ross" or "Gap"
            # don't match as substrings inside longer words (e.g. "Cross", "Gapski").
            # The \b anchor only fires at letter/digit↔non-letter/digit boundaries,
            # so "Ross Dress" still matches, but "Celtic Cross" does not.
            patterns.append(re.compile(r'\b' + re.escape(line) + r'\b', re.IGNORECASE))
    return patterns

def is_chain(business_name, patterns):
    low = business_name.lower().strip()
    if low in FALSE_POSITIVES:
        return False
    for pat in patterns:
        if pat.search(business_name):
            return True
    return False

def process_csv(path, patterns, removed_log):
    try:
        with open(path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return 0, 0
            fieldnames = [fn for fn in reader.fieldnames if fn is not None and fn != '']
            rows = [{k: v for k, v in r.items() if k is not None and k != ''} for r in reader]
    except Exception as e:
        print(f'  ERROR reading {path}: {e}')
        return 0, 0

    kept = []
    removed = []
    for row in rows:
        name = row.get('business_name', '').strip()
        if is_chain(name, patterns):
            removed.append(row)
            removed_log.append({
                'business_name': name,
                'neighborhood': row.get('neighborhood', ''),
                'category': row.get('category', ''),
                'source_file': os.path.relpath(path, REPO_ROOT),
            })
        else:
            kept.append(row)

    if removed and not DRY_RUN:
        tmp = str(path) + '.tmp'
        clean_rows = [{k: v for k, v in r.items() if k is not None and k != ''} for r in kept]
        with open(tmp, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(clean_rows)
        os.replace(tmp, path)

    return len(kept), len(removed)

def main():
    if not BLOCKLIST_PATH.exists():
        print(f'ERROR: blocklist not found at {BLOCKLIST_PATH}')
        sys.exit(1)

    patterns = load_blocklist(BLOCKLIST_PATH)
    print(f'Loaded {len(patterns)} chain patterns from blocklist')
    if DRY_RUN:
        print('DRY RUN — no files will be modified')
    print()

    all_csvs = sorted(glob.glob(str(REPO_ROOT / '**' / '*.csv'), recursive=True))
    # Exclude the removed_chains log itself and data/master
    all_csvs = [p for p in all_csvs if 'removed_chains' not in p]

    removed_log = []
    total_removed = 0
    total_kept = 0
    report_lines = []

    # Process master CSV first
    master = str(REPO_ROOT / 'data' / 'master-prospects.csv')
    if master in all_csvs:
        all_csvs.remove(master)
        all_csvs.insert(0, master)

    for path in all_csvs:
        kept, removed = process_csv(path, patterns, removed_log)
        total_kept += kept
        total_removed += removed
        rel = os.path.relpath(path, REPO_ROOT)
        if removed:
            report_lines.append(f'  {rel}: removed {removed}, kept {kept}')
            print(f'  REMOVED {removed:2d} from {rel}')

    print()
    print(f'=== Chain filter summary ===')
    print(f'Total rows removed:  {total_removed}')
    print(f'Total rows kept:     {total_kept}')
    print()
    if report_lines:
        print('Files with removals:')
        for line in report_lines:
            print(line)
    else:
        print('No chains found in any CSV.')

    if removed_log and not DRY_RUN:
        with open(REMOVED_LOG_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['business_name', 'neighborhood', 'category', 'source_file'])
            writer.writeheader()
            writer.writerows(removed_log)
        print(f'\nRemoval log written to {REMOVED_LOG_PATH}')

    return total_removed, removed_log

if __name__ == '__main__':
    main()
