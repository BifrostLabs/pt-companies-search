#!/usr/bin/env python3
"""
Enrich company data with additional info from nif.pt API
"""

import json
import time
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def lookup_nif(nif: str) -> dict | None:
    """
    Look up company details via nif.pt
    
    Note: nif.pt has rate limits. For bulk lookups, consider:
    - Their paid API
    - lookuptax.com API
    - Commercial providers (HitHorizons, etc.)
    """
    url = f"https://www.nif.pt/api/v1/search"
    
    # nif.pt has a public search but may require API key for programmatic access
    # This is a placeholder - check their current API terms
    
    try:
        # Alternative: use their validation endpoint
        response = requests.get(
            f"https://www.nif.pt/{nif}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10
        )
        
        # The page returns HTML with company info if valid
        # For production, use their API or parse the response
        return {
            "nif": nif,
            "validated": response.status_code == 200
        }
        
    except Exception as e:
        print(f"  ⚠️  Error looking up {nif}: {e}")
        return None


def enrich_companies(input_file: str, limit: int = 10):
    """Enrich companies with additional data"""
    
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    companies = data["companies"][:limit]
    print(f"🔍 Enriching {len(companies)} companies...")
    
    enriched = []
    for i, company in enumerate(companies):
        print(f"  [{i+1}/{len(companies)}] {company['nif']} - {company['name'][:30]}...")
        
        extra = lookup_nif(company["nif"])
        if extra:
            company["enriched"] = extra
        
        enriched.append(company)
        
        # Rate limit protection
        time.sleep(1)
    
    # Save enriched data
    output_file = input_file.replace(".json", "_enriched.json")
    data["companies"] = enriched
    data["enriched_count"] = len(enriched)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved enriched data to {output_file}")
    return enriched


def filter_by_activity(companies: list, keywords: list) -> list:
    """Filter companies by activity keywords in name"""
    keywords_lower = [k.lower() for k in keywords]
    
    filtered = []
    for company in companies:
        name_lower = company["name"].lower()
        if any(kw in name_lower for kw in keywords_lower):
            filtered.append(company)
    
    return filtered


def main():
    import glob
    
    # Find latest companies file
    files = sorted(glob.glob(str(DATA_DIR / "companies_*.json")), reverse=True)
    if not files:
        print("❌ No company data found. Run scraper.py first.")
        return
    
    latest = files[0].replace("_enriched", "")
    print(f"📁 Using: {latest}")
    
    # Load and analyze
    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    companies = data["companies"]
    
    # Example: Filter by activity
    print("\n🏗️  Construction companies:")
    construction = filter_by_activity(companies, ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS"])
    for c in construction[:10]:
        print(f"   • {c['nif']} | {c['name'][:50]}")
    
    print(f"\n   Total: {len(construction)} construction companies")
    
    print("\n💻 Tech/IT companies:")
    tech = filter_by_activity(companies, ["TECH", "DIGITAL", "SOFTWARE", "IT ", "SOLUTIONS", "INFORMATICA", "COMPUTER"])
    for c in tech[:10]:
        print(f"   • {c['nif']} | {c['name'][:50]}")
    
    print(f"\n   Total: {len(tech)} tech companies")
    
    print("\n🍽️  Food/Hospitality companies:")
    food = filter_by_activity(companies, ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "TUR"])
    for c in food[:10]:
        print(f"   • {c['nif']} | {c['name'][:50]}")
    
    print(f"\n   Total: {len(food)} food/hospitality companies")
    
    # Optional: Enrich a sample
    print("\n" + "="*50)
    user_input = input("\n🔍 Enrich first 10 companies with nif.pt? (y/N): ")
    if user_input.lower() == "y":
        enrich_companies(latest, limit=10)


if __name__ == "__main__":
    main()
