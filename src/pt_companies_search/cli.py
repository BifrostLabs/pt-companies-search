"""
CLI Entry Point for PT Companies Search
"""

import argparse
import sys
from datetime import datetime, date
from pathlib import Path

from pt_companies_search.core.config import config
from pt_companies_search.core.database import test_connection, upsert_company, route_company_by_contact
from pt_companies_search.scraper.einforma import fetch_all_companies, save_daily_snapshot
from pt_companies_search.scraper.nif import search_multiple_pages
from pt_companies_search.enricher.nif_enrich import RateLimiter, enrich_company, wait_for_available_slot
from pt_companies_search.utils.helpers import extract_city, extract_postal_code, get_sector

def run_scraper(args):
    max_pages = getattr(args, 'pages', None) or config.SCRAPER_MAX_PAGES
    print(f"[scrape] Fetching from eInforma.pt (up to {max_pages} pages)...")
    companies = fetch_all_companies(max_pages=max_pages, delay=config.SCRAPER_DELAY)
    if not companies:
        print("[scrape] No companies found.")
        return

    print(f"[scrape] Found {len(companies)} companies.")
    save_daily_snapshot(companies)

    if test_connection():
        print("[scrape] Saving to database...")
        saved = 0
        for c in companies:
            c['source'] = 'einforma'
            c['source_url'] = c.get('url')
            # eInforma dates are DD-MM-YYYY — convert to ISO YYYY-MM-DD for PostgreSQL
            raw_date = c.get('date', '')
            try:
                c['registration_date'] = datetime.strptime(raw_date, '%d-%m-%Y').date().isoformat()
            except (ValueError, TypeError):
                c['registration_date'] = None
            c['sector'] = get_sector(c.get('name', ''))
            upsert_company(c)
            saved += 1
        print(f"[scrape] Saved {saved} companies.")
    print("[scrape] Done.")

def run_search(args):
    print(f"[search] Searching NIF.pt for '{args.query}'...")
    companies = search_multiple_pages(args.query, args.pages, args.delay)
    if not companies:
        print("[search] No companies found.")
        return

    print(f"[search] Found {len(companies)} unique companies.")

    if test_connection():
        print("[search] Saving to database...")
        for c in companies:
            c['source'] = 'nif_search'
            c['source_url'] = c.get('url')
            c['city'] = extract_city(c.get('location', ''))
            c['postal_code'] = extract_postal_code(c.get('location', ''))
            c['sector'] = get_sector(c.get('name', ''))
            upsert_company(c)
    print("[search] Done.")

def run_enrich(args):
    if not config.NIF_API_KEY:
        print("[enrich] NIF_API_KEY not set.")
        return

    from pt_companies_search.core.database import search_companies, route_company_by_contact
    from pt_companies_search.enricher.key_rotation import APIKeyRotator, load_api_keys

    companies = search_companies(
        source=args.source,
        limit=args.limit,
        is_enriched=False,
        exclude_outro=args.dashboard_only
    )
    if not companies:
        print("[enrich] No companies to enrich.")
        return

    try:
        key_rotator = APIKeyRotator(load_api_keys())
        print(key_rotator.get_status_report())
    except Exception as e:
        print(f"[enrich] Key rotation not available: {e}. Using single key.")
        key_rotator = None

    rate_limiter = RateLimiter()
    print(f"[enrich] Starting enrichment for {len(companies)} companies...")

    for i, company in enumerate(companies, 1):
        if not wait_for_available_slot(rate_limiter, verbose=True):
            break

        api_key = key_rotator.get_current_key() if key_rotator else config.NIF_API_KEY
        print(f"[{i}/{len(companies)}] {company['nif']} - {company['name']}")
        enriched = enrich_company(company['nif'], api_key, rate_limiter)

        if enriched:
            enriched['source'] = 'nif_api'
            enriched['sector'] = get_sector(enriched.get('name', ''), enriched.get('cae'))
            table = route_company_by_contact(enriched)
            print(f"   -> saved to {table} (sector: {enriched['sector']})")
        else:
            print(f"   -> failed")
            if key_rotator:
                key_rotator.rotate_key()
                print(key_rotator.get_status_report())

def main():
    parser = argparse.ArgumentParser(description="PT Companies Search CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape eInforma.pt")
    scrape_parser.add_argument("--pages", type=int, default=5, help="Max pages to scrape (default: 5)")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search NIF.pt")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--pages", type=int, default=10)
    search_parser.add_argument("--delay", type=float, default=2.0)
    
    # Enrich command
    enrich_parser = subparsers.add_parser("enrich", help="Enrich data using NIF.pt API")
    enrich_parser.add_argument("--source", default=None)
    enrich_parser.add_argument("--limit", type=int, default=50)
    enrich_parser.add_argument("--dashboard-only", action="store_true", default=True, help="Only enrich companies that match a dashboard sector")
    enrich_parser.add_argument("--all-sectors", action="store_false", dest="dashboard_only", help="Enrich all companies regardless of sector")
    
    args = parser.parse_args()
    
    if args.command == "scrape":
        run_scraper(args)
    elif args.command == "search":
        run_search(args)
    elif args.command == "enrich":
        run_enrich(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
