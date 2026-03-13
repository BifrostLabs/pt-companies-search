"""
CLI Entry Point for PT Companies Search
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

from pt_companies_search.core.config import config
from pt_companies_search.core.database import test_connection, upsert_company, route_company_by_contact
from pt_companies_search.scraper.einforma import fetch_new_companies, save_daily_snapshot
from pt_companies_search.scraper.nif import search_multiple_pages
from pt_companies_search.enricher.nif_enrich import RateLimiter, enrich_company, wait_for_available_slot
from pt_companies_search.utils.helpers import extract_city, extract_postal_code, get_sector

def run_scraper(args):
    print("🔍 Fetching new companies from eInforma.pt...")
    companies = fetch_new_companies()
    if not companies:
        print("❌ No companies found.")
        return
    
    print(f"📊 Found {len(companies)} companies.")
    save_daily_snapshot(companies)
    
    if test_connection():
        print("🗄️ Saving to database...")
        for c in companies:
            c['source'] = 'einforma'
            c['source_url'] = c.get('url')
            c['registration_date'] = c.get('date')
            c['sector'] = get_sector(c.get('name', ''))
            upsert_company(c)
    print("✅ Done.")

def run_search(args):
    print(f"🔍 Searching NIF.pt for '{args.query}'...")
    companies = search_multiple_pages(args.query, args.pages, args.delay)
    if not companies:
        print("❌ No companies found.")
        return
    
    print(f"📊 Found {len(companies)} unique companies.")
    
    if test_connection():
        print("🗄️ Saving to database...")
        for c in companies:
            c['source'] = 'nif_search'
            c['source_url'] = c.get('url')
            c['city'] = extract_city(c.get('location', ''))
            c['postal_code'] = extract_postal_code(c.get('location', ''))
            c['sector'] = get_sector(c.get('name', ''))
            upsert_company(c)
    print("✅ Done.")

def run_enrich(args):
    if not config.NIF_API_KEY:
        print("❌ NIF_API_KEY not set.")
        return
    
    from pt_companies_search.core.database import search_companies, route_company_by_contact
    from pt_companies_search.enricher.key_rotation import APIKeyRotator, load_api_keys
    
    # Get companies that haven't been enriched yet, optionally filtering by dashboard sectors
    companies = search_companies(
        source=args.source, 
        limit=args.limit,
        is_enriched=False,
        exclude_outro=args.dashboard_only
    )
    if not companies:
        print("✅ No companies to enrich.")
        return
    
    # Initialize key rotator
    try:
        key_rotator = APIKeyRotator(load_api_keys())
        print(key_rotator.get_status_report())
    except Exception as e:
        print(f"⚠️  Key rotation not available: {e}")
        print("Using single API key mode")
        key_rotator = None
    
    rate_limiter = RateLimiter()
    print(f"🚀 Starting enrichment for {len(companies)} companies...")
    
    for i, company in enumerate(companies, 1):
        if not wait_for_available_slot(rate_limiter, verbose=True):
            break
        
        # Get current API key (with rotation support)
        if key_rotator:
            api_key = key_rotator.get_current_key()
        else:
            api_key = config.NIF_API_KEY
            
        print(f"[{i}/{len(companies)}] Enriching {company['nif']} - {company['name']}...")
        enriched = enrich_company(company['nif'], api_key, rate_limiter)
        
        if enriched:
            enriched['source'] = 'nif_api'
            table = route_company_by_contact(enriched)
            if table == "companies":
                print(f"   ✅ Saved to main table (has contact)")
            elif table == "leads_without_personal_data":
                print(f"   ✅ Saved to leads table (no contact)")
            else:
                print(f"   ❌ Failed to save")
        else:
            print(f"   ❌ Failed")
            
            # If enrichment failed, try rotating the key
            if key_rotator:
                key_rotator.rotate_key()
                print(key_rotator.get_status_report())

def main():
    parser = argparse.ArgumentParser(description="PT Companies Search CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Scrape command
    scrape_parser = subparsers.add_parser("scrape", help="Scrape eInforma.pt")
    
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
