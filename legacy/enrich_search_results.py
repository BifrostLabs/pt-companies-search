#!/usr/bin/env python3
"""
Enrich NIF.pt search results with full contact details
"""

import json
import sys
from pathlib import Path
from nif_enrich import enrich_company, RateLimiter, load_config

DATA_DIR = Path(__file__).parent / "data"


def load_search_results():
    """Load all NIF.pt search results"""
    import glob
    
    search_files = sorted(glob.glob(str(DATA_DIR / "nif_search_*.json")), reverse=True)
    if not search_files:
        return []
    
    all_companies = []
    for search_file in search_files:
        with open(search_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_companies.extend(data.get("companies", []))
    
    # Remove duplicates by NIF
    unique = {}
    for company in all_companies:
        nif = company.get("nif")
        if nif and nif not in unique:
            unique[nif] = company
    
    return list(unique.values())


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich NIF.pt search results")
    parser.add_argument("--limit", type=int, default=0, help="Limit number to enrich (0=all)")
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    api_key = config.get("api_key")
    
    if not api_key:
        print("❌ No API key. Run: pt-nif-enrich --setup")
        return
    
    # Load search results
    companies = load_search_results()
    print(f"📂 Found {len(companies)} companies from search results")
    
    if not companies:
        print("❌ No search results found. Run: pt-nif-search 'QUERY'")
        return
    
    # Limit
    if args.limit > 0:
        companies = companies[:args.limit]
        print(f"   Limited to: {args.limit} companies")
    
    # Initialize rate limiter
    rate_limiter = RateLimiter()
    rate_limiter.display_status()
    
    # Load existing enriched data
    enriched_file = DATA_DIR / "companies_enriched.json"
    if enriched_file.exists():
        with open(enriched_file, "r", encoding="utf-8") as f:
            enriched_data = json.load(f)
    else:
        enriched_data = {"companies": {}, "metadata": {}}
    
    # Enrich
    print(f"\n🚀 Enriching {len(companies)} companies...")
    
    success = 0
    failed = 0
    skipped = 0
    
    for i, company in enumerate(companies, 1):
        nif = company["nif"]
        name = company.get("name", "Unknown")[:40]
        
        # Skip if already enriched
        if nif in enriched_data["companies"]:
            skipped += 1
            continue
        
        print(f"\n[{i}/{len(companies)}] {nif} - {name}...")
        
        # Enrich
        enriched = enrich_company(nif, api_key, rate_limiter)
        
        if enriched:
            # Merge with search data
            enriched["search_location"] = company.get("location")
            enriched["search_url"] = company.get("url")
            enriched_data["companies"][nif] = enriched
            success += 1
            
            # Show key fields
            if enriched.get("phone"):
                print(f"   📞 {enriched['phone']}")
            if enriched.get("email"):
                print(f"   ✉️  {enriched['email']}")
            if enriched.get("address"):
                print(f"   📍 {enriched['address']}")
        else:
            failed += 1
        
        # Save every 5
        if i % 5 == 0:
            with open(enriched_file, "w", encoding="utf-8") as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)
            print(f"\n💾 Progress saved ({i}/{len(companies)})")
    
    # Final save
    with open(enriched_file, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 Enrichment Summary")
    print(f"{'='*50}")
    print(f"   ✅ Enriched: {success}")
    print(f"   ❌ Failed: {failed}")
    print(f"   ⏭️  Skipped: {skipped}")
    print(f"   📊 Total: {len(enriched_data['companies'])}")
    print(f"   💾 Saved to: {enriched_file}")


if __name__ == "__main__":
    main()
