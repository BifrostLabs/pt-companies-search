#!/usr/bin/env python3
"""
NIF.pt Search Scraper
Search and scrape companies directly from NIF.pt database
Saves to both JSON and PostgreSQL (when available)
"""

import re
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict
from html.parser import HTMLParser

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# Standard sector definitions
SECTORS = {
    "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL"],
    "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS"],
    "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO"],
    "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO", "MEDIÇÃO IMOBILIÁRIA"],
    "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA"],
}


def get_sector(name: str) -> str:
    """Classify company into sector"""
    if not name:
        return "Outro"
    name_upper = name.upper()
    for sector, keywords in SECTORS.items():
        if any(kw in name_upper for kw in keywords):
            return sector
    return "Outro"


def extract_city(location: str) -> str:
    """Extract city from location string"""
    if not location or location == "N/A":
        return ""
    parts = location.split(maxsplit=1)
    if len(parts) > 1:
        return parts[1]
    return ""


def extract_postal_code(location: str) -> str:
    """Extract postal code from location string"""
    if not location or location == "N/A":
        return ""
    parts = location.split(maxsplit=1)
    if len(parts) > 0:
        return parts[0]
    return ""


class NIFSearchParser(HTMLParser):
    """Parse NIF.pt search results"""
    
    def __init__(self):
        super().__init__()
        self.companies = []
        self.current_company = None
        self.in_search_title = False
        self.current_data = []
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        
        # Company links have class='search-title'
        if tag == "a" and attrs_dict.get("class") == "search-title":
            href = attrs_dict.get("href", "")
            # Extract NIF from href like /508832020/
            match = re.match(r'^/(\d{9})/$', href)
            if match:
                self.in_search_title = True
                nif = match.group(1)
                self.current_company = {
                    "nif": nif,
                    "url": f"https://www.nif.pt{href}"
                }
                self.current_data = []
    
    def handle_data(self, data):
        data = data.strip()
        
        if not data:
            return
        
        if self.in_search_title and self.current_company and not self.current_company.get("name"):
            # Company name
            self.current_company["name"] = data
            self.in_search_title = False
        
        elif self.current_company and self.current_company.get("name"):
            # Collect data after company name
            self.current_data.append(data)
    
    def handle_endtag(self, tag):
        if tag == "p" and self.current_company:
            # End of company paragraph - parse collected data
            # Pattern: "NIF: 508832020" followed by location
            nif_text = None
            location = None
            
            for data in self.current_data:
                if data.startswith("NIF:"):
                    nif_text = data
                elif re.match(r'^\d{4}-\d{3}', data):
                    location = data
            
            if nif_text and location:
                self.current_company["nif_text"] = nif_text
                self.current_company["location"] = location
                self.companies.append(self.current_company)
            
            # Reset for next company
            self.current_company = None
            self.current_data = []


def search_nif_pt(query: str, page: int = 1) -> List[Dict]:
    """
    Search NIF.pt for companies
    
    Args:
        query: Search term (company name, keyword, etc.)
        page: Page number (starts at 1)
    
    Returns:
        List of companies with NIF, name, location, URL
    """
    url = "https://www.nif.pt/"
    
    params = {"q": query}
    if page > 1:
        params["page"] = page
    
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; PTCompanyTracker/1.0)"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        
        parser = NIFSearchParser()
        parser.feed(response.text)
        
        return parser.companies
        
    except requests.RequestException as e:
        print(f"❌ Error searching NIF.pt: {e}")
        return []


def search_multiple_pages(query: str, max_pages: int = 10, delay: float = 2.0) -> List[Dict]:
    """
    Search multiple pages of results
    
    Args:
        query: Search term
        max_pages: Maximum pages to scrape
        delay: Delay between requests (seconds)
    
    Returns:
        List of all companies found
    """
    all_companies = []
    
    print(f"🔍 Searching NIF.pt for: '{query}'")
    
    for page in range(1, max_pages + 1):
        print(f"   Page {page}...", end=" ", flush=True)
        
        companies = search_nif_pt(query, page)
        
        if not companies:
            print("No more results")
            break
        
        all_companies.extend(companies)
        print(f"Found {len(companies)} companies (total: {len(all_companies)})")
        
        # Be respectful - delay between requests
        if page < max_pages:
            time.sleep(delay)
    
    return all_companies


def save_to_json(companies: List[Dict], query: str) -> Path:
    """Save search results to JSON file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nif_search_{query.replace(' ', '_')}_{timestamp}.json"
    output_file = DATA_DIR / filename
    
    data = {
        "search_query": query,
        "search_date": datetime.now().isoformat(),
        "total_results": len(companies),
        "companies": companies
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved {len(companies)} companies to {output_file}")
    return output_file


def save_to_database(companies: List[Dict]) -> int:
    """Save search results to PostgreSQL database"""
    try:
        from db import transaction
        
        count = 0
        with transaction() as conn:
            with conn.cursor() as cur:
                for company in companies:
                    nif = company.get("nif")
                    name = company.get("name", "Unknown")
                    location = company.get("location", "")
                    url = company.get("url", "")
                    
                    city = extract_city(location)
                    postal_code = extract_postal_code(location)
                    sector = get_sector(name)
                    
                    # Upsert company
                    cur.execute("""
                        INSERT INTO companies (
                            nif, name, source, source_url, 
                            city, postal_code, sector, fetched_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (nif) DO UPDATE SET
                            name = EXCLUDED.name,
                            source_url = COALESCE(EXCLUDED.source_url, companies.source_url),
                            city = COALESCE(EXCLUDED.city, companies.city),
                            postal_code = COALESCE(EXCLUDED.postal_code, companies.postal_code),
                            sector = COALESCE(EXCLUDED.sector, companies.sector),
                            last_verified_at = NOW()
                    """, (nif, name, 'nif_search', url, city, postal_code, sector))
                    count += 1
                
                # ✅ FIX: transaction() auto-commits!
        
        print(f"🗄️ Saved {count} companies to PostgreSQL")
        return count
        
    except Exception as e:
        print(f"⚠️  Database save failed: {e}")
        return 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Search NIF.pt for companies")
    parser.add_argument("query", help="Search term (company name, keyword)")
    parser.add_argument("--pages", type=int, default=10, help="Maximum pages to scrape (default: 10)")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between requests in seconds (default: 2.0)")
    parser.add_argument("--output", help="Output filename (default: auto-generated)")
    parser.add_argument("--no-db", action="store_true", help="Skip saving to database")
    args = parser.parse_args()
    
    # Search
    companies = search_multiple_pages(args.query, args.pages, args.delay)
    
    if not companies:
        print("\n❌ No companies found")
        return
    
    # Remove duplicates by NIF
    unique_companies = {}
    for company in companies:
        nif = company["nif"]
        if nif not in unique_companies:
            unique_companies[nif] = company
    
    companies = list(unique_companies.values())
    
    print(f"\n📊 Found {len(companies)} unique companies")
    
    # Save to JSON
    if args.output:
        output_file = DATA_DIR / args.output
        data = {
            "search_query": args.query,
            "search_date": datetime.now().isoformat(),
            "total_results": len(companies),
            "companies": companies
        }
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"💾 Saved {len(companies)} companies to {output_file}")
    else:
        save_to_json(companies, args.query)
    
    # Save to database
    if not args.no_db:
        save_to_database(companies)
    
    # Show sample
    print(f"\n📋 Sample companies:")
    for company in companies[:10]:
        print(f"   • {company['nif']} | {company.get('location', 'N/A'):30s} | {company['name'][:50]}")


if __name__ == "__main__":
    main()
