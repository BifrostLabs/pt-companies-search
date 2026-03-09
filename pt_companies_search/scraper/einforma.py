"""
Portugal New Companies Scraper
Fetches newly registered companies from eInforma.pt
"""

import re
import json
import requests
from datetime import datetime
from pathlib import Path
from html.parser import HTMLParser
from typing import Optional, List, Dict, Any, Tuple

from pt_companies_search.core.config import config

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
            
            if "/servlet/app/portal/ENTP/prod/ETIQUETA_EMPRESA/nif/" in href:
                self.in_company_link = True
                match = re.search(r'/nif/(\d{9})', href)
                if match:
                    self.current_company = {
                        "nif": match.group(1),
                        "url": f"https://www.einforma.pt{href}"
                    }
    
    def handle_data(self, data):
        if self.in_company_link and self.current_company:
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


def fetch_new_companies() -> List[Dict[str, Any]]:
    """Fetch the list of new companies from eInforma.pt"""
    url = "https://www.einforma.pt/novas-empresas-portuguesas"
    headers = {"User-Agent": config.USER_AGENT}
    
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    parser = CompanyListParser()
    parser.feed(response.text)
    
    return parser.companies


def load_historical_data() -> dict:
    """Load accumulated historical data"""
    historical_file = Path(config.DATA_DIR) / "companies_historical.json"
    if historical_file.exists():
        with open(historical_file, "r", encoding="utf-8") as f:
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
    historical_file = Path(config.DATA_DIR) / "companies_historical.json"
    historical_file.parent.mkdir(exist_ok=True, parents=True)
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    data["metadata"]["total_unique"] = len(data["companies"])
    
    with open(historical_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def merge_new_companies(historical: dict, new_companies: list) -> Tuple[int, int]:
    """Merge new companies into historical data"""
    new_count = 0
    updated_count = 0
    
    for company in new_companies:
        nif = company["nif"]
        
        if nif not in historical["companies"]:
            historical["companies"][nif] = {
                **company,
                "first_seen": datetime.now().isoformat(),
                "data_source": ["eInforma.pt - Novas Empresas"]
            }
            new_count += 1
        else:
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
    
    output_file = Path(config.DATA_DIR) / f"companies_{date_str}.json"
    output_file.parent.mkdir(exist_ok=True, parents=True)
    
    data = {
        "fetch_date": datetime.now().isoformat(),
        "source": "https://www.einforma.pt/novas-empresas-portuguesas",
        "count": len(companies),
        "companies": companies
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_file
