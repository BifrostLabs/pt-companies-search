#!/usr/bin/env python3
"""
Portugal New Companies - Full Automation
One command to scrape, search, enrich, and save to DB

Usage:
    pt-automate                  # Run all steps with defaults
    pt-automate --skip-scrape    # Skip eInforma.pt scraping
    pt-automate --search-only    # Only search NIF.pt (no enrichment)
    pt-automate --enrich-limit 50  # Limit enrichment to 50 companies
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import List, Optional

# Import local modules
sys.path.insert(0, str(Path(__file__).parent))

from scraper import (
    fetch_new_companies,
    load_historical_data,
    save_historical_data,
    merge_new_companies,
    save_daily_snapshot,
)
from nif_search import search_multiple_pages
from nif_enrich import (
    RateLimiter,
    load_config,
    load_companies_to_enrich,
    load_enriched_data,
    save_enriched_data,
    enrich_company,
    wait_for_available_slot,
    merge_enriched_data,
)
from db import test_connection, get_cursor
from db_loader import is_db_available


# Default search keywords (configurable)
DEFAULT_SEARCH_KEYWORDS = [
    # High-value sectors
    "TECNOLOGIA",
    "SOFTWARE",
    "CONSULTORIA",
    "CONSTRUCAO",
    
    # Regional (optional - uncomment to enable)
    # "RESTAURANTE",
    # "HOTEL",
    # "IMOBILIARIA",
]


def print_header(title: str):
    """Print formatted section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_step(step: int, total: int, message: str):
    """Print step indicator"""
    print(f"\n[Step {step}/{total}] {message}")
    print("-" * 60)


def check_prerequisites() -> bool:
    """Check if all prerequisites are met"""
    print("🔍 Checking prerequisites...")
    
    issues = []
    
    # Check API key
    config = load_config()
    if not config.get("api_key"):
        issues.append("❌ NIF.pt API key not configured. Run: pt-nif-enrich --setup")
    else:
        print("✅ NIF.pt API key configured")
    
    # Check database
    if is_db_available():
        print("✅ PostgreSQL database available")
    else:
        print("⚠️  PostgreSQL not available (will save to JSON only)")
    
    # Check rate limits
    rate_limiter = RateLimiter()
    usage = rate_limiter.get_usage()
    if usage["month"]["remaining"] == 0:
        issues.append(f"❌ Monthly API quota exhausted ({usage['month']['used']}/{usage['month']['limit']})")
    else:
        print(f"✅ API quota available: {usage['month']['remaining']}/{usage['month']['limit']} remaining this month")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   {issue}")
        return False
    
    return True


def step_scrape() -> dict:
    """Step 1: Scrape eInforma.pt for new companies"""
    print("📡 Scraping eInforma.pt for new companies...")
    
    try:
        # Fetch new companies
        companies = fetch_new_companies()
        
        if not companies:
            print("ℹ️  No new companies found")
            return {"companies": [], "new_count": 0, "total_historical": 0}
        
        # Save daily snapshot
        save_daily_snapshot(companies)
        print(f"✅ Saved daily snapshot: {len(companies)} companies")
        
        # Accumulate into historical data
        historical = load_historical_data()
        new_count, updated_count = merge_new_companies(historical, companies)
        save_historical_data(historical)
        
        print(f"✅ Historical data updated:")
        print(f"   • New: {new_count}")
        print(f"   • Updated: {updated_count}")
        print(f"   • Total unique: {len(historical['companies'])}")
        
        # Show sample
        print("\n   Sample companies:")
        for company in companies[:5]:
            print(f"   • {company['nif']} | {company['date']} | {company['name'][:50]}")
        
        if len(companies) > 5:
            print(f"   ... and {len(companies) - 5} more")
        
        return {
            "companies": companies,
            "new_count": new_count,
            "total_historical": len(historical['companies'])
        }
        
    except Exception as e:
        print(f"❌ Error scraping: {e}")
        return {"companies": [], "new_count": 0, "total_historical": 0}


def step_search(keywords: List[str], max_pages: int = 5) -> int:
    """Step 2: Search NIF.pt for companies by keyword"""
    if not keywords:
        print("⏭️  Skipping NIF.pt search (no keywords configured)")
        return 0
    
    print(f"🔍 Searching NIF.pt for {len(keywords)} keywords...")
    
    total_found = 0
    for keyword in keywords:
        print(f"\n   Searching: {keyword}")
        try:
            # Search multiple pages
            results = search_multiple_pages(keyword, max_pages=max_pages, delay=2.0)
            if results:
                total_found += len(results)
                print(f"   ✅ Found {len(results)} companies")
            else:
                print(f"   ℹ️  No results")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n✅ Total found via search: {total_found}")
    return total_found


def step_enrich(limit: int = 0, force: bool = False) -> int:
    """Step 3: Enrich companies with contact details"""
    print("🔄 Enriching companies with contact details...")
    
    # Load data
    config = load_config()
    api_key = config.get("api_key")
    
    if not api_key:
        print("❌ No API key configured")
        return 0
    
    rate_limiter = RateLimiter()
    
    # Show rate limit status
    usage = rate_limiter.get_usage()
    print(f"\n📊 API Quota Status:")
    print(f"   Monthly: {usage['month']['used']}/{usage['month']['limit']} ({usage['month']['remaining']} remaining)")
    print(f"   Daily: {usage['day']['used']}/{usage['day']['limit']}")
    print(f"   Hourly: {usage['hour']['used']}/{usage['hour']['limit']}")
    
    # Load companies to enrich
    companies = load_companies_to_enrich("historical")
    enriched_data = load_enriched_data()
    
    if not companies:
        print("ℹ️  No companies to enrich")
        return 0
    
    # Filter out already enriched (unless force)
    if not force:
        to_enrich = [c for c in companies if c.get("nif") not in enriched_data["companies"]]
    else:
        to_enrich = companies
    
    if not to_enrich:
        print("✅ All companies already enriched")
        return 0
    
    # Apply limit
    if limit > 0:
        to_enrich = to_enrich[:limit]
    
    print(f"\n📋 Companies to enrich: {len(to_enrich)}")
    
    # Check if we have enough quota
    if usage["month"]["remaining"] < len(to_enrich):
        print(f"⚠️  Not enough monthly quota. Will enrich {usage['month']['remaining']} companies.")
        to_enrich = to_enrich[:usage["month"]["remaining"]]
    
    # Enrich
    enriched_count = 0
    for i, company in enumerate(to_enrich, 1):
        nif = company.get("nif")
        name = company.get("name", "Unknown")
        
        print(f"\n[{i}/{len(to_enrich)}] {nif}: {name[:50]}")
        
        # Wait for available slot
        if not wait_for_available_slot(rate_limiter, verbose=False):
            print("   ⏸️  Rate limit reached, stopping enrichment")
            break
        
        # Enrich
        enriched = enrich_company(nif, api_key, rate_limiter)
        
        if enriched:
            # Merge and save
            merged = merge_enriched_data(company, enriched)
            enriched_data["companies"][nif] = enriched
            
            # Save after each successful enrichment
            save_enriched_data(enriched_data)
            
            enriched_count += 1
            
            # Show progress
            has_contact = "📞" if enriched.get("phone") or enriched.get("email") else "📭"
            print(f"   ✅ Enriched {has_contact}")
        else:
            print(f"   ❌ No data found")
    
    print(f"\n✅ Enriched {enriched_count}/{len(to_enrich)} companies")
    return enriched_count


def step_sync() -> dict:
    """Step 4: Sync all data to PostgreSQL"""
    print("🗄️  Syncing data to PostgreSQL...")
    
    if not is_db_available():
        print("⚠️  PostgreSQL not available, skipping sync")
        return {"total": 0, "enriched": 0}
    
    with get_cursor() as cur:
        # Get stats
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(enriched_at) as enriched,
                COUNT(CASE WHEN phone IS NOT NULL OR email IS NOT NULL THEN 1 END) as with_contact
            FROM companies
        """)
        stats = dict(cur.fetchone())
    
    print(f"✅ Database stats:")
    print(f"   Total companies: {stats['total']}")
    print(f"   Enriched: {stats['enriched']}")
    print(f"   With contact info: {stats['with_contact']}")
    
    return stats


def generate_report(scrape_result: dict, search_count: int, enrich_count: int, db_stats: dict):
    """Generate final summary report"""
    print_header("📊 Summary Report")
    
    print(f"📅 Run completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print("📌 Results:")
    print(f"   • New from eInforma.pt: {len(scrape_result.get('companies', []))}")
    print(f"   • Found via NIF.pt search: {search_count}")
    print(f"   • Enriched this run: {enrich_count}")
    
    if db_stats:
        print(f"\n🗄️  Database:")
        print(f"   • Total companies: {db_stats['total']}")
        print(f"   • Enriched: {db_stats['enriched']}")
        print(f"   • With contact info: {db_stats['with_contact']}")
    
    # Rate limit status
    rate_limiter = RateLimiter()
    usage = rate_limiter.get_usage()
    
    print(f"\n📊 API Quota Remaining:")
    print(f"   • Monthly: {usage['month']['remaining']}/{usage['month']['limit']}")
    print(f"   • Daily: {usage['day']['remaining']}/{usage['day']['limit']}")
    print(f"   • Hourly: {usage['hour']['remaining']}/{usage['hour']['limit']}")
    
    print("\n✅ Automation complete!\n")


def main():
    parser = argparse.ArgumentParser(
        description="Automate scraping, searching, and enrichment",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  pt-automate                      # Run all steps
  pt-automate --skip-scrape        # Skip eInforma.pt scraping
  pt-automate --skip-search        # Skip NIF.pt search
  pt-automate --search-only        # Only search, no enrichment
  pt-automate --enrich-limit 50    # Enrich max 50 companies
  pt-automate --keywords "HOTEL RESTAURANTE"  # Custom keywords
        """
    )
    
    # Step control
    parser.add_argument("--skip-scrape", action="store_true", help="Skip eInforma.pt scraping")
    parser.add_argument("--skip-search", action="store_true", help="Skip NIF.pt search")
    parser.add_argument("--skip-enrich", action="store_true", help="Skip enrichment")
    parser.add_argument("--search-only", action="store_true", help="Only search NIF.pt (no enrichment)")
    
    # Options
    parser.add_argument("--enrich-limit", type=int, default=0, help="Limit number of companies to enrich (0 = all available quota)")
    parser.add_argument("--enrich-force", action="store_true", help="Re-enrich already enriched companies")
    parser.add_argument("--search-pages", type=int, default=5, help="Max pages per search keyword (default: 5)")
    parser.add_argument("--keywords", type=str, help="Custom search keywords (space-separated)")
    parser.add_argument("--no-check", action="store_true", help="Skip prerequisite checks")
    
    args = parser.parse_args()
    
    # Print header
    print_header("🇵🇹 Portugal New Companies - Automation")
    
    # Check prerequisites
    if not args.no_check:
        if not check_prerequisites():
            print("\n❌ Prerequisites not met. Fix issues above or use --no-check to continue anyway.")
            return 1
    
    # Determine keywords
    if args.keywords:
        keywords = args.keywords.upper().split()
    else:
        keywords = DEFAULT_SEARCH_KEYWORDS
    
    # Track results
    scrape_result = {}
    search_count = 0
    enrich_count = 0
    
    # Calculate total steps
    total_steps = 0
    if not args.skip_scrape:
        total_steps += 1
    if not args.skip_search:
        total_steps += 1
    if not args.skip_enrich and not args.search_only:
        total_steps += 1
    total_steps += 1  # Always sync
    
    current_step = 0
    
    # Step 1: Scrape eInforma.pt
    if not args.skip_scrape:
        current_step += 1
        print_step(current_step, total_steps, "Scraping eInforma.pt")
        scrape_result = step_scrape()
    
    # Step 2: Search NIF.pt
    if not args.skip_search:
        current_step += 1
        print_step(current_step, total_steps, "Searching NIF.pt")
        search_count = step_search(keywords, max_pages=args.search_pages)
    
    # Step 3: Enrich
    if not args.skip_enrich and not args.search_only:
        current_step += 1
        print_step(current_step, total_steps, "Enriching companies")
        enrich_count = step_enrich(limit=args.enrich_limit, force=args.enrich_force)
    
    # Step 4: Sync to DB
    current_step += 1
    print_step(current_step, total_steps, "Syncing to database")
    db_stats = step_sync()
    
    # Generate report
    generate_report(scrape_result, search_count, enrich_count, db_stats)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
