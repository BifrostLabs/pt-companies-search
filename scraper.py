#!/usr/bin/env python3
"""
Portugal New Companies Scraper
Fetches newly registered companies from eInforma.pt
Supports historical data accumulation
"""

import re
import json
import requests
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser
from typing import Optional

DATA_DIR = Path(__file__).parent / "data"
HISTORICAL_FILE = DATA_DIR / "companies_historical.json"
DATA_DIR.mkdir(exist_ok=True)


class CompanyListParser(HTMLParser):
    """Parse the new companies list from eInforma.pt"""
    
    def __init__(self):
        super().__init__()
        self.companies = []
        self.current_company = None
        self.in_company_link = False
        
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            attrs_dict = dict(attrs)
            href = attrs_dict.get("href", "")
            
            # Match company links with NIF
            if "/servlet/app/portal/ENTP/prod/ETIQUETA_EMPRESA/nif/" in href:
                self.in_company_link = True
                # Extract NIF from URL
                match = re.search(r'/nif/(\d{9})', href)
                if match:
                    self.current_company = {
                        "nif": match.group(1),
                        "url": f"https://www.einforma.pt{href}"
                    }
    
    def handle_data(self, data):
        if self.in_company_link and self.current_company:
            # Parse: "03-03-2026 - COMPANY NAME"
            match = re.match(r'(\d{2}-\d{2}-\d{4})\s*-\s*(.+)', data.strip())
            if match:
                self.current_company["date"] = match.group(1)
                self.current_company["name"] = match.group(2).strip()
    
    def handle_endtag(self, tag):
        if tag == "a" and self.in_company_link:
            self.in_company_link = False
            if self.current_company and "name" in self.current_company:
                self.companies.append(self.current_company)
            self.current_company = None


def fetch_new_companies():
    """Fetch the list of new companies from eInforma.pt"""
    url = "https://www.einforma.pt/novas-empresas-portuguesas"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PTCompanyTracker/1.0)"
    }
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    parser = CompanyListParser()
    parser.feed(response.text)
    
    return parser.companies


def load_historical_data() -> dict:
    """Load accumulated historical data"""
    if HISTORICAL_FILE.exists():
        with open(HISTORICAL_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "companies": {},
        "metadata": {
            "created": datetime.now().isoformat(),
            "last_updated": None,
            "total_unique": 0
        }
    }


def save_historical_data(data: dict):
    """Save accumulated historical data"""
    HISTORICAL_FILE.parent.mkdir(exist_ok=True)
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    data["metadata"]["total_unique"] = len(data["companies"])
    
    with open(HISTORICAL_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_new_companies(historical: dict, new_companies: list) -> tuple[int, int]:
    """Merge new companies into historical data. Returns (new_count, updated_count)"""
    new_count = 0
    updated_count = 0
    
    for company in new_companies:
        nif = company["nif"]
        
        if nif not in historical["companies"]:
            # New company
            historical["companies"][nif] = {
                **company,
                "first_seen": datetime.now().isoformat(),
                "data_source": ["eInforma.pt - Novas Empresas"]
            }
            new_count += 1
        else:
            # Update existing (in case of data changes)
            existing = historical["companies"][nif]
            if existing.get("name") != company.get("name"):
                existing["name"] = company["name"]
                existing["url"] = company["url"]
                updated_count += 1
    
    return new_count, updated_count


def save_daily_snapshot(companies: list, date_str: Optional[str] = None):
    """Save a daily snapshot of the data"""
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    output_file = DATA_DIR / f"companies_{date_str}.json"
    
    data = {
        "fetch_date": datetime.now().isoformat(),
        "source": "https://www.einforma.pt/novas-empresas-portuguesas",
        "count": len(companies),
        "companies": companies
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Saved {len(companies)} companies to {output_file}")
    return output_file


def get_all_historical_companies() -> list:
    """Get all companies from historical data"""
    historical = load_historical_data()
    return list(historical["companies"].values())


def get_companies_by_year(year: int) -> list:
    """Filter companies by registration year"""
    all_companies = get_all_historical_companies()
    
    filtered = []
    for company in all_companies:
        date_str = company.get("date", "")
        if date_str:
            try:
                # Parse DD-MM-YYYY format
                date_parts = date_str.split("-")
                if len(date_parts) == 3:
                    company_year = int(date_parts[2])
                    if company_year == year:
                        filtered.append(company)
            except (ValueError, IndexError):
                continue
    
    return filtered


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Scrape new Portuguese companies")
    parser.add_argument("--no-accumulate", action="store_true", help="Skip historical accumulation")
    parser.add_argument("--year", type=int, help="Show companies from specific year (from historical data)")
    parser.add_argument("--stats", action="store_true", help="Show historical data statistics")
    args = parser.parse_args()
    
    # Show stats mode
    if args.stats:
        historical = load_historical_data()
        print(f"\n📊 Historical Data Statistics:")
        print(f"   Total unique companies: {historical['metadata']['total_unique']}")
        print(f"   Last updated: {historical['metadata']['last_updated'] or 'Never'}")
        
        # Count by year
        companies = list(historical["companies"].values())
        by_year = {}
        for c in companies:
            date_str = c.get("date", "")
            if date_str:
                try:
                    year = date_str.split("-")[2]
                    by_year[year] = by_year.get(year, 0) + 1
                except IndexError:
                    pass
        
        if by_year:
            print(f"\n   By year:")
            for year in sorted(by_year.keys()):
                print(f"      {year}: {by_year[year]} companies")
        
        return
    
    # Year filter mode
    if args.year:
        companies = get_companies_by_year(args.year)
        print(f"\n📋 Companies from {args.year}: {len(companies)} found")
        
        if companies:
            for c in companies[:10]:
                print(f"   • {c['nif']} | {c['date']} | {c['name'][:50]}")
            
            if len(companies) > 10:
                print(f"   ... and {len(companies) - 10} more")
        
        return
    
    # Normal fetch mode
    print("🔍 Fetching new Portuguese companies from eInforma.pt...")
    
    try:
        companies = fetch_new_companies()
        
        if not companies:
            print("❌ No companies found. The page structure may have changed.")
            return
        
        # Group by date
        by_date = {}
        for company in companies:
            date = company.get("date", "unknown")
            if date not in by_date:
                by_date[date] = []
            by_date[date].append(company)
        
        print(f"\n📊 Found {len(companies)} new companies:")
        for date, comps in sorted(by_date.items(), reverse=True):
            print(f"   {date}: {len(comps)} companies")
        
        # Save daily snapshot
        save_daily_snapshot(companies)
        
        # Accumulate into historical data
        if not args.no_accumulate:
            print("\n📚 Accumulating into historical data...")
            historical = load_historical_data()
            new_count, updated_count = merge_new_companies(historical, companies)
            save_historical_data(historical)
            
            print(f"   ✅ Added {new_count} new companies")
            if updated_count > 0:
                print(f"   🔄 Updated {updated_count} existing companies")
            print(f"   📊 Total unique companies: {len(historical['companies'])}")
        
        # Show sample
        print(f"\n📋 Sample companies (latest 5):")
        for company in companies[:5]:
            print(f"   • {company['nif']} | {company['date']} | {company['name'][:50]}...")
        
        return companies
        
    except requests.RequestException as e:
        print(f"❌ Network error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        raise


if __name__ == "__main__":
    main()
