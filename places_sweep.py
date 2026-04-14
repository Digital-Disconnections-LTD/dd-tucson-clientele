#!/usr/bin/env python3
"""
Google Places API (New) sweep for Tucson, AZ prospects.
DIG-788
"""

import csv
import json
import os
import time
import urllib.request
import urllib.parse
from pathlib import Path

API_KEY = "AIzaSyBOrdVg6EVDX5tcZ0qPqO3aUzClC3BF2as"
NEARBY_URL = "https://places.googleapis.com/v1/places:searchNearby"
TEXT_URL   = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.internationalPhoneNumber,places.websiteUri,"
    "places.rating,places.userRatingCount,places.types"
)

# Zones: (zone_key, folder_name, lat, lng, radius_meters)
# Priority order: affluent neighborhoods first
ZONES = [
    # Wave 1 — Affluent areas
    ("catalina-foothills",       "catalina-foothills",        32.3300, -110.8900, 5000),
    ("oro-valley",               "oro-valley",                32.3909, -110.9665, 5000),
    ("tanque-verde-sabino",      "tanque-verde-sabino",       32.2700, -110.7800, 5000),
    ("sam-hughes-university",    "sam-hughes-university",     32.2260, -110.9490, 3500),
    ("casas-adobes",             "casas-adobes",              32.3405, -111.0130, 4500),

    # Wave 2 — Established business corridors
    ("fourth-ave-downtown",      "fourth-ave-downtown",       32.2275, -110.9700, 3000),
    ("dove-mountain-marana",     "dove-mountain-marana",      32.4100, -111.0720, 5000),
    ("broadway-corridor",        "broadway-corridor",         32.2217, -110.9200, 4000),

    # Wave 3 — Suburban growth areas
    ("rita-ranch-vail",          "rita-ranch-vail",           32.0650, -110.8100, 5000),
    ("sahuarita-green-valley",   "sahuarita-green-valley",   31.9400, -110.9600, 6000),
]

TYPES = [
    "restaurant", "bar", "cafe", "bakery", "meal_delivery", "meal_takeaway",
    "hair_salon", "nail_salon", "beauty_salon", "spa", "barber_shop",
    "dentist", "doctor", "physiotherapist", "optician",
    "clothing_store", "jewelry_store", "florist", "book_store", "gift_shop",
    "car_repair", "car_wash",
    "laundry", "dry_cleaning", "locksmith", "tailor", "pet_store",
    "general_contractor",
]

CSV_HEADER = [
    "business_name", "address", "phone", "category", "neighborhood",
    "google_maps_url", "website_url", "quality_score", "platform",
    "est_monthly_cost", "pain_points", "priority_rank", "outreach_doc_ready",
    "place_id", "rating", "user_ratings_total",
]

PROSPECTS_DIR = Path(__file__).parent / "prospects"


def post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": API_KEY,
            "X-Goog-FieldMask": FIELD_MASK,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def nearby_search_all(lat, lng, radius, btype):
    payload = {
        "includedTypes": [btype],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": float(radius),
            }
        },
        "maxResultCount": 20,
        "rankPreference": "DISTANCE",
    }
    try:
        data = post_json(NEARBY_URL, payload)
        return data.get("places", [])
    except Exception as e:
        print(f"    nearby_search error ({btype}): {e}")
        return []


def text_search_all(query):
    results = []
    payload = {"textQuery": query, "maxResultCount": 20}
    while True:
        try:
            data = post_json(TEXT_URL, payload)
        except Exception as e:
            print(f"    text_search error ({query}): {e}")
            break
        results.extend(data.get("places", []))
        token = data.get("nextPageToken")
        if not token or len(data.get("places", [])) == 0:
            break
        payload = {"textQuery": query, "maxResultCount": 20, "pageToken": token}
        time.sleep(2)
    return results


def score_business(website):
    if not website:
        return 1, "no website"
    return 2, "has website"


def load_existing_ids(csv_path):
    ids = set()
    if not csv_path.exists():
        return ids
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("place_id", "").strip()
            if pid:
                ids.add(pid)
    return ids


def count_rows(csv_path):
    if not csv_path.exists():
        return 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in f) - 1


def migrate_csv_if_needed(csv_path):
    if not csv_path.exists():
        return
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        rows = list(reader)
    needs_update = any(c not in fields for c in ["place_id", "rating", "user_ratings_total"])
    if needs_update:
        print(f"    Migrating {csv_path.name} to add new columns...")
        for row in rows:
            row.setdefault("place_id", "")
            row.setdefault("rating", "")
            row.setdefault("user_ratings_total", "")
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
            writer.writeheader()
            writer.writerows(rows)


def append_rows(csv_path, rows):
    exists = csv_path.exists()
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADER)
        if not exists:
            writer.writeheader()
        writer.writerows(rows)


def place_to_row(p, btype, folder_name, rank):
    name     = p.get("displayName", {}).get("text", "").strip()
    address  = p.get("formattedAddress", "").strip()
    phone    = p.get("internationalPhoneNumber", "").strip()
    website  = p.get("websiteUri", "").strip()
    rating   = p.get("rating", "")
    reviews  = p.get("userRatingCount", "")
    place_id = p.get("id", "").strip()

    score, pain = score_business(website)
    maps_url = f"https://maps.google.com/?q={urllib.parse.quote(name + ' ' + address)}"

    return {
        "business_name":      name,
        "address":            address,
        "phone":              phone,
        "category":           btype,
        "neighborhood":       folder_name,
        "google_maps_url":    maps_url,
        "website_url":        website,
        "quality_score":      score,
        "platform":           "",
        "est_monthly_cost":   0,
        "pain_points":        pain,
        "priority_rank":      rank,
        "outreach_doc_ready": "false",
        "place_id":           place_id,
        "rating":             rating,
        "user_ratings_total": reviews,
    }


def main():
    total_added = 0
    zone_summary = {}

    for zone_key, folder_name, lat, lng, radius in ZONES:
        folder = PROSPECTS_DIR / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        csv_path = folder / f"{folder_name}-prospects.csv"

        migrate_csv_if_needed(csv_path)
        existing_ids = load_existing_ids(csv_path)
        rank = count_rows(csv_path) + 1

        zone_new = 0
        seen_this_zone = set(existing_ids)

        print(f"\n=== Zone: {zone_key} ===")

        for btype in TYPES:
            places = nearby_search_all(lat, lng, radius, btype)
            print(f"  {btype}: {len(places)} results", end="")

            new_rows = []
            for p in places:
                pid = p.get("id", "")
                if not pid or pid in seen_this_zone:
                    continue
                seen_this_zone.add(pid)
                row = place_to_row(p, btype, folder_name, rank)
                new_rows.append(row)
                rank += 1

            if new_rows:
                append_rows(csv_path, new_rows)
                zone_new += len(new_rows)
                print(f" → +{len(new_rows)} new")
            else:
                print(f" → 0 new (all dupes or no id)")

            time.sleep(0.15)

        print(f"  Zone total: +{zone_new}")
        zone_summary[zone_key] = zone_new
        total_added += zone_new

    print("\n=== SWEEP COMPLETE ===")
    for z, n in zone_summary.items():
        print(f"  {z}: +{n}")
    print(f"  TOTAL NEW: {total_added}")

    return zone_summary, total_added


if __name__ == "__main__":
    main()
