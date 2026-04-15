#!/usr/bin/env python3
"""
Enrich Tucson prospect CSVs with:
1. Registrar detection (via whois) for businesses with website URLs
2. Platform detection (via curl headers/body) for businesses with unknown platform
3. Domain availability suggestions for businesses with no website (score=1)
"""

import csv
import subprocess
import re
import time
import sys
from urllib.parse import urlparse
from pathlib import Path

BASE = Path(__file__).parent / "prospects"

WHOIS_DELAY = 1.0
CURL_TIMEOUT = 10


def find_all_csvs():
    return sorted(BASE.rglob("*-prospects.csv"))


def extract_domain(url_field):
    if not url_field:
        return None
    val = url_field.strip()
    if val.lower() in ('none', 'n/a', ''):
        return None
    val = re.sub(r'\s*\([^)]*\)\s*', '', val).strip()
    if not val:
        return None
    if not val.startswith(('http://', 'https://')):
        val = 'http://' + val
    try:
        parsed = urlparse(val)
        domain = parsed.netloc.lower()
        domain = re.sub(r'^www\.', '', domain)
        domain = domain.split(':')[0]
        return domain if domain and '.' in domain else None
    except Exception:
        return None


def get_registrar(domain):
    try:
        result = subprocess.run(
            ['whois', domain],
            capture_output=True, text=True, timeout=20
        )
        output = result.stdout
        if re.search(r'no match|not found|no entries found|status:\s*free', output, re.IGNORECASE):
            return 'unregistered'
        for line in output.splitlines():
            m = re.match(r'^\s*registrar:\s*(.+)', line, re.IGNORECASE)
            if m:
                name = m.group(1).strip()
                if 'IANA' not in name.upper():
                    name = re.sub(r',\s*(LLC|Inc\.?|Corp\.?|Ltd\.?).*$', '', name, flags=re.IGNORECASE).strip()
                    return name[:60] if name else 'unknown'
        return 'unknown'
    except subprocess.TimeoutExpired:
        return 'timeout'
    except Exception:
        return 'error'


def detect_platform(domain):
    url = f'https://{domain}'
    try:
        r = subprocess.run(
            ['curl', '-sI', '-L', '--max-time', str(CURL_TIMEOUT), url],
            capture_output=True, text=True, timeout=CURL_TIMEOUT + 5
        )
        headers = r.stdout.lower()
        r2 = subprocess.run(
            ['curl', '-s', '-L', '--max-time', str(CURL_TIMEOUT),
             '--max-filesize', '100000', url],
            capture_output=True, text=True, timeout=CURL_TIMEOUT + 5
        )
        body = r2.stdout.lower()[:15000]
        if not headers and not body:
            return 'no response'
        if 'x-wix-request-id' in headers or 'wixstatic.com' in body or \
           ('wix.com' in body and 'static.wixstatic' in body):
            return 'wix'
        if ('x-served-by' in headers and 'squarespace' in headers) or \
           'static1.squarespace.com' in body or 'squarespace.com/static' in body or \
           'squarespace' in headers:
            return 'squarespace'
        if 'x-shopid' in headers or 'x-shopify' in headers or \
           'cdn.shopify.com' in body or 'shopify.com' in body:
            return 'shopify'
        if 'webflow' in headers or 'webflow.com' in body:
            return 'webflow'
        if 'weebly.com' in body or 'editmysite.com' in body:
            return 'weebly'
        if 'wp-content' in body or 'wp-includes' in body or \
           ('x-powered-by: php' in headers and 'wordpress' in body):
            return 'wordpress'
        if 'godaddysites.com' in body or 'x-go-dc-userid' in headers:
            return 'godaddy'
        if 'x-generator: joomla' in headers or \
           ('<meta name="generator" content="joomla' in body):
            return 'joomla'
        if 'x-drupal' in headers or 'drupal.js' in body or \
           '<meta name="generator" content="drupal' in body:
            return 'drupal'
        if 'duda' in headers or 'dudaone.com' in body:
            return 'duda'
        if 'google.com/sites' in body or 'sites.google.com' in body:
            return 'google sites'
        if 'x-powered-by: php' in headers:
            return 'custom php'
        if body.strip():
            return 'custom/unknown'
        return 'no response'
    except subprocess.TimeoutExpired:
        return 'timeout'
    except Exception:
        return 'unknown'


def name_to_slug(name):
    s = name.lower()
    s = re.sub(r"'s\b", 's', s)
    for w in [' llc', ' inc', ' corp', ' co ', ' & co', ' the ', 'the ']:
        s = s.replace(w, ' ')
    s = re.sub(r'[^a-z0-9]', '', s)
    return s


def check_domain_available(candidate):
    try:
        result = subprocess.run(
            ['whois', candidate],
            capture_output=True, text=True, timeout=20
        )
        out = result.stdout + result.stderr
        if re.search(r'no match|not found|no entries found|status:\s*free|is available|not registered',
                     out, re.IGNORECASE):
            return True
        if re.search(r'registrar:|domain name:|creation date:|registered on:',
                     out, re.IGNORECASE):
            return False
        return None
    except subprocess.TimeoutExpired:
        return None
    except Exception:
        return None


def get_domain_suggestions(business_name, n=2):
    slug = name_to_slug(business_name)
    if not slug or len(slug) < 2:
        return ''
    candidates = [
        f"{slug}.com",
        f"{slug}tucson.com",
        f"{slug}az.com",
        f"{slug}arizona.com",
    ]
    available = []
    for c in candidates:
        if len(available) >= n:
            break
        status = check_domain_available(c)
        print(f"      whois {c} -> {'available' if status else 'taken' if status is False else 'unclear'}", flush=True)
        time.sleep(WHOIS_DELAY)
        if status:
            available.append(c)
    return '; '.join(available) if available else 'all taken'


def enrich_file(path):
    path = Path(path)
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        orig_fields = list(reader.fieldnames or [])
        rows = list(reader)

    out_fields = list(orig_fields)
    if 'registrar' not in out_fields:
        try:
            idx = out_fields.index('platform') + 1
        except ValueError:
            idx = len(out_fields)
        out_fields.insert(idx, 'registrar')
    if 'domain_suggestions' not in out_fields:
        out_fields.append('domain_suggestions')

    summary = []
    enriched = []

    for row in rows:
        name = row.get('business_name', '').strip()
        url_field = row.get('website_url', '').strip()
        score = row.get('quality_score', '').strip()
        platform_cur = row.get('platform', '').strip()
        registrar_cur = row.get('registrar', '').strip()
        domain_suggestions_cur = row.get('domain_suggestions', '').strip()
        domain = extract_domain(url_field)

        # Skip rows already fully enriched — avoids re-running whois on Wave 1 data
        already_enriched = registrar_cur and registrar_cur.lower() not in ('', 'unknown', 'error', 'timeout')
        already_has_suggestions = domain_suggestions_cur and domain_suggestions_cur not in ('', 'all taken')

        if domain:
            if already_enriched and platform_cur.lower() not in ('unknown', '', 'none', 'n/a'):
                print(f"  [{name}] already enriched — skipping", flush=True)
                row.setdefault('domain_suggestions', '')
                summary.append((name, 'skipped', f"already enriched: {registrar_cur}, {platform_cur}"))
                enriched.append(row)
                continue
            print(f"  [{name}] has domain: {domain}", flush=True)
            registrar = get_registrar(domain)
            time.sleep(WHOIS_DELAY)
            print(f"    registrar: {registrar}", flush=True)
            if platform_cur.lower() in ('unknown', '', 'none', 'n/a'):
                detected = detect_platform(domain)
                print(f"    platform detected: {detected}", flush=True)
                if detected not in ('unknown', 'no response', 'timeout', 'error', ''):
                    row['platform'] = detected
                    summary.append((name, 'platform+registrar', f"{detected}, {registrar}"))
                else:
                    summary.append((name, 'registrar', registrar))
            else:
                summary.append((name, 'registrar', f"{registrar} (platform was: {platform_cur})"))
            row['registrar'] = registrar
            row.setdefault('domain_suggestions', '')
        elif score == '1':
            print(f"  [{name}] no website, generating suggestions...", flush=True)
            suggestions = get_domain_suggestions(name)
            row.setdefault('registrar', '')
            row['domain_suggestions'] = suggestions
            summary.append((name, 'domain_suggestions', suggestions))
        else:
            row.setdefault('registrar', '')
            row.setdefault('domain_suggestions', '')
            summary.append((name, 'skipped', f"score={score}, no url"))

        enriched.append(row)

    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(enriched)

    return summary


def main():
    csv_files = find_all_csvs()
    if not csv_files:
        print("No prospect CSVs found. Run places_sweep.py first.")
        return {}

    all_summaries = {}
    for csv_path in csv_files:
        neighborhood = csv_path.parent.name
        print(f"\n{'='*60}", flush=True)
        print(f"Enriching: {csv_path.name}  ({neighborhood})", flush=True)
        print('='*60, flush=True)
        try:
            summary = enrich_file(csv_path)
            all_summaries[neighborhood] = summary
            print(f"\n  -> Done: {len(summary)} businesses processed", flush=True)
        except Exception as e:
            print(f"  ERROR processing {csv_path}: {e}", flush=True)
            import traceback; traceback.print_exc()

    print("\n\n" + "="*60, flush=True)
    print("ENRICHMENT SUMMARY", flush=True)
    print("="*60, flush=True)
    for hood, items in all_summaries.items():
        print(f"\n{hood.upper()}", flush=True)
        for name, action, detail in items:
            print(f"  {name[:35]:<35} [{action}] {detail}", flush=True)

    return all_summaries


if __name__ == '__main__':
    main()
