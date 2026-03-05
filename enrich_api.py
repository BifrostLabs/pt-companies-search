#!/usr/bin/env python3
"""
Company Data Enrichment Script
Enriches company data with additional information from NIF.pt API
"""

import json
import time
import requests
from pathlib import Path
from typing import Optional, Dict

DATA_DIR = Path(__file__).parent / "data"

# NIF.pt API Configuration
# Get your free API key at: https://www.nif.pt/contactos/api/
NIF_API_KEY = None  # Set this to your API key

# Rate limiting (free tier: 1 per minute, 10 per hour, 100 per day)
RATE_LIMIT_SECONDS = 60  # 1 request per minute for free tier


def load_api_key():
    """Load API key from config file or environment"""
    global NIF_API_KEY
    
    # Try loading from config file
    config_file = Path(__file__).parent / "config.json"
    if config_file.exists():
        with open(config_file, "r") as f:
            config = json.load(f)
            NIF_API_KEY = config.get("nif_api_key")
    
    return NIF_API_KEY


def enrich_company_from_nif_pt(nif: str, api_key: Optional[str] = None) -> Optional[Dict]:
    """
    Fetch company details from NIF.pt API
    
    Args:
        nif: 9-digit Portuguese tax ID
        api_key: NIF.pt API key (optional, uses global if not provided)
    
    Returns:
        Dictionary with company data or None if not found
    """
    key = api_key or NIF_API_KEY
    
    if not key:
        print("❌ No API key configured. Get one at: https://www.nif.pt/contactos/api/")
        return None
    
    url = f"http://www.nif.pt/?json=1&q={nif}&key={key}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if data.get("result") == "success" and data.get("records"):
            company_data = data["records"].get(str(nif))
            
            if company_data:
                return {
                    "nif": nif,
                    "name": company_data.get("title"),
                    "address": company_data.get("address") or company_data.get("place", {}).get("address"),
                    "postal_code": f"{company_data.get('pc4', '')}-{company_data.get('pc3', '')}",
                    "city": company_data.get("city") or company_data.get("place", {}).get("city"),
                    "region": company_data.get("geo", {}).get("region"),
                    "county": company_data.get("geo", {}).get("county"),
                    "parish": company_data.get("geo", {}).get("parish"),
                    "phone": company_data.get("contacts", {}).get("phone"),
                    "email": company_data.get("contacts", {}).get("email"),
                    "website": company_data.get("contacts", {}).get("website"),
                    "fax": company_data.get("contacts", {}).get("fax"),
                    "activity": company_data.get("activity"),
                    "cae": company_data.get("cae"),
                    "legal_form": company_data.get("structure", {}).get("nature"),
                    "capital": company_data.get("structure", {}).get("capital"),
                    "capital_currency": company_data.get("structure", {}).get("capital_currency"),
                    "status": company_data.get("status"),
                }
        
        return None
        
    except requests.RequestException as e:
        print(f"❌ Error fetching {nif}: {e}")
        return None


def enrich_companies_batch(nifs: list, limit: int = None, delay: float = RATE_LIMIT_SECONDS):
    """
    Enrich multiple companies with rate limiting
    
    Args:
        nifs: List of NIFs to enrich
        limit: Maximum number to process (None = all)
        delay: Seconds to wait between requests (default: 60 for free tier)
    
    Returns:
        Dictionary mapping NIF to enriched data
    """
    if not load_api_key():
        return {}
    
    enriched = {}
    to_process = nifs[:limit] if limit else nifs
    
    print(f"🔍 Enriching {len(to_process)} companies...")
    print(f"⏱️  Rate limit: {delay}s between requests (estimated time: {len(to_process) * delay / 60:.1f} minutes)")
    print()
    
    for i, nif in enumerate(to_process, 1):
        print(f"[{i}/{len(to_process)}] Fetching {nif}...", end=" ")
        
        data = enrich_company_from_nif_pt(nif)
        
        if data:
            enriched[nif] = data
            print(f"✅ {data.get('name', 'N/A')[:40]}")
        else:
            print("❌ Not found")
        
        # Rate limiting
        if i < len(to_process):
            time.sleep(delay)
    
    return enriched


def save_enriched_data(enriched: dict, output_file: str = None):
    """Save enriched data to JSON file"""
    if not output_file:
        from datetime import datetime
        output_file = DATA_DIR / f"enriched_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    output_file = Path(output_file)
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "enriched_date": datetime.now().isoformat(),
            "count": len(enriched),
            "companies": enriched
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Saved {len(enriched)} enriched companies to {output_file}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich company data from NIF.pt API")
    parser.add_argument("--nif", type=str, help="Single NIF to enrich")
    parser.add_argument("--file", type=str, help="JSON file with company data")
    parser.add_argument("--limit", type=int, help="Limit number of companies to enrich")
    parser.add_argument("--key", type=str, help="NIF.pt API key (overrides config)")
    parser.add_argument("--delay", type=float, default=RATE_LIMIT_SECONDS, help="Delay between requests (seconds)")
    parser.add_argument("--output", type=str, help="Output file path")
    
    args = parser.parse_args()
    
    # Set API key if provided
    if args.key:
        global NIF_API_KEY
        NIF_API_KEY = args.key
    
    # Single NIF mode
    if args.nif:
        data = enrich_company_from_nif_pt(args.nif)
        if data:
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Company {args.nif} not found")
        return
    
    # Batch mode from file
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            file_data = json.load(f)
        
        # Extract NIFs from various formats
        if "companies" in file_data:
            # Our format
            companies = file_data["companies"]
            if isinstance(companies, list):
                nifs = [c["nif"] for c in companies if "nif" in c]
            else:
                nifs = list(companies.keys())
        else:
            print("❌ Unsupported file format")
            return
        
        # Enrich
        enriched = enrich_companies_batch(nifs, limit=args.limit, delay=args.delay)
        
        # Save
        if enriched:
            save_enriched_data(enriched, args.output)
    
    else:
        print("❌ Please provide --nif or --file")
        print("\nExamples:")
        print("  # Single company")
        print("  python enrich_api.py --nif 519280458 --key YOUR_KEY")
        print()
        print("  # Batch enrichment")
        print("  python enrich_api.py --file data/companies_2026-03-05.json --limit 10 --key YOUR_KEY")


if __name__ == "__main__":
    main()
