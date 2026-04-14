#!/usr/bin/env python3
"""
Build Tucson outreach shortlist from master-prospects.csv.

Tiered prioritization per DIG-800:
  Tier 1 — No website (highest conversion potential)
  Tier 2 — Weak-platform sites (Wix, Weebly, template builders)
  Tier 3 — WordPress / Squarespace / Drupal (redesign potential)

Within each tier, ranked by:
  1. Business type: professional services > beauty/retail > food & auto
  2. Zone affluence: Catalina Foothills > Oro Valley > Tanque Verde > Casas Adobes > Sam Hughes
  3. Engagement: review count (proxy for established + active)
  4. Google rating
"""

import csv
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(REPO, "data", "master-prospects.csv")
OUT_PATH = os.path.join(REPO, "data", "shortlist.csv")

TARGET_MIN = 40
TARGET_MAX = 60

# Tier 2 weak platforms
TIER2_PLATFORMS = {"wix", "weebly"}

# Tier 3 platforms (capable but often overbuilt / outdated)
TIER3_PLATFORMS = {"wordpress", "squarespace", "drupal"}

# Category score — higher = more likely to invest in a quality site
CATEGORY_SCORE = {
    # Professional services — highest margins, reputation-sensitive
    "doctor":           30,
    "dentist":          30,
    "physiotherapist":  28,
    "optician":         27,
    # High-end beauty
    "spa":              25,
    "beauty_salon":     24,
    # Standard beauty / personal care
    "hair_salon":       22,
    "nail_salon":       20,
    "barber_shop":      18,
    # Retail — tangible goods, often high transaction value
    "jewelry_store":    20,
    "clothing_store":   18,
    "florist":          17,
    "gift_shop":        15,
    "book_store":       14,
    "pet_store":        13,
    # Home & auto services
    "general_contractor": 15,
    "locksmith":        14,
    "car_repair":       12,
    "dry_cleaning":     11,
    "tailor":           10,
    "laundry":          9,
    # Food & beverage — lower margin, high competition
    "bakery":           12,
    "cafe":             10,
    "restaurant":       10,
    "bar":              9,
    "meal_delivery":    7,
    "meal_takeaway":    7,
}

# Zone affluence score
ZONE_SCORE = {
    "catalina-foothills":    30,
    "oro-valley":            25,
    "tanque-verde-sabino":   20,
    "casas-adobes":          15,
    "sam-hughes-university": 10,
}

# Tier base scores
TIER_BASE = {1: 60, 2: 30, 3: 15}


def review_score(count_str):
    try:
        n = int(count_str.strip())
    except (ValueError, AttributeError):
        return 0
    if n >= 500:
        return 20
    if n >= 200:
        return 15
    if n >= 100:
        return 10
    if n >= 50:
        return 5
    if n >= 1:
        return 2
    return 0


def rating_score(rating_str):
    try:
        r = float(rating_str.strip())
    except (ValueError, AttributeError):
        return 0
    if r >= 4.5:
        return 10
    if r >= 4.0:
        return 7
    if r >= 3.5:
        return 4
    return 0


def assign_tier(row):
    pain = row.get("pain_points", "").strip().lower()
    platform = row.get("platform", "").strip().lower()
    if pain == "no website":
        return 1
    if platform in TIER2_PLATFORMS:
        return 2
    if platform in TIER3_PLATFORMS:
        return 3
    return 0  # ineligible


def first_domain_suggestion(row):
    suggestions = row.get("domain_suggestions", "").strip()
    if not suggestions:
        return ""
    # Semicolon-separated list, take the first
    parts = [p.strip() for p in suggestions.split(";") if p.strip()]
    return parts[0] if parts else ""


def build_rationale(row, tier, score):
    zone_display = {
        "catalina-foothills": "Catalina Foothills",
        "oro-valley": "Oro Valley",
        "tanque-verde-sabino": "Tanque Verde",
        "casas-adobes": "Casas Adobes",
        "sam-hughes-university": "Sam Hughes/University",
    }.get(row.get("neighborhood", ""), row.get("neighborhood", ""))

    cat = row.get("category", "").replace("_", " ")
    rating = row.get("rating", "").strip()
    reviews = row.get("user_ratings_total", "").strip()
    platform = row.get("platform", "").strip() or "no platform"

    rating_str = f"{rating}★" if rating else "no rating"
    review_str = f"{reviews} reviews" if reviews else "no reviews"

    if tier == 1:
        return (
            f"Tier 1 — no website; {cat} in {zone_display}, "
            f"{rating_str} {review_str}"
        )
    elif tier == 2:
        return (
            f"Tier 2 — {platform} site; {cat} in {zone_display}, "
            f"{rating_str} {review_str} — upgrade from template"
        )
    else:
        return (
            f"Tier 3 — {platform}; {cat} in {zone_display}, "
            f"{rating_str} {review_str} — redesign opportunity"
        )


def main():
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    candidates = []
    for row in all_rows:
        tier = assign_tier(row)
        if tier == 0:
            continue

        cat_pts = CATEGORY_SCORE.get(row.get("category", "").strip(), 8)
        zone_pts = ZONE_SCORE.get(row.get("neighborhood", "").strip(), 5)
        rev_pts = review_score(row.get("user_ratings_total", ""))
        rat_pts = rating_score(row.get("rating", ""))
        base_pts = TIER_BASE[tier]

        total_score = base_pts + cat_pts + zone_pts + rev_pts + rat_pts

        candidates.append({
            "_row": row,
            "_tier": tier,
            "_score": total_score,
        })

    # Sort: tier ASC (Tier 1 first), then score DESC
    candidates.sort(key=lambda c: (c["_tier"], -c["_score"]))

    # Select 50 prospects, balanced across tiers
    # Fill Tier 1 first up to ~20, then Tier 2 up to ~15, Tier 3 up to ~15
    tier_targets = {1: 20, 2: 15, 3: 15}
    tier_buckets = {1: [], 2: [], 3: []}
    for c in candidates:
        t = c["_tier"]
        if len(tier_buckets[t]) < tier_targets[t]:
            tier_buckets[t].append(c)

    total_selected = sum(len(b) for b in tier_buckets.values())

    # If under target, fill from overflow in order
    if total_selected < TARGET_MIN:
        already_selected = set(
            id(c) for bucket in tier_buckets.values() for c in bucket
        )
        for c in candidates:
            if id(c) not in already_selected and total_selected < TARGET_MAX:
                tier_buckets[c["_tier"]].append(c)
                total_selected += 1

    # Flatten and re-sort by tier then score for final output
    shortlist = []
    for tier in (1, 2, 3):
        shortlist.extend(tier_buckets[tier])
    shortlist.sort(key=lambda c: (c["_tier"], -c["_score"]))

    print(f"Shortlist: {len(shortlist)} prospects")
    for t in (1, 2, 3):
        n = len([c for c in shortlist if c["_tier"] == t])
        print(f"  Tier {t}: {n}")

    # Write shortlist.csv
    fieldnames = [
        "business_name", "zone", "tier", "score", "platform",
        "domain_suggestion", "google_rating", "review_count",
        "category", "google_maps_url", "rationale",
    ]

    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rank, c in enumerate(shortlist, 1):
            row = c["_row"]
            writer.writerow({
                "business_name": row.get("business_name", ""),
                "zone": row.get("neighborhood", ""),
                "tier": c["_tier"],
                "score": c["_score"],
                "platform": row.get("platform", "") or "none",
                "domain_suggestion": first_domain_suggestion(row),
                "google_rating": row.get("rating", ""),
                "review_count": row.get("user_ratings_total", ""),
                "category": row.get("category", ""),
                "google_maps_url": row.get("google_maps_url", ""),
                "rationale": build_rationale(row, c["_tier"], c["_score"]),
            })

    print(f"\nWrote {OUT_PATH}")


if __name__ == "__main__":
    main()
