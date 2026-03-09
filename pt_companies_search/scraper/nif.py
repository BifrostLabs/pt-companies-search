"""
NIF.pt Search Scraper
Search and scrape companies directly from NIF.pt database
"""

import re
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
from html.parser import HTMLParser

from pt_companies_search.core.config import config
from pt_companies_search.core.database import transaction

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
        
        if tag == "a" and attrs_dict.get("class") == "search-title":
            href = attrs_dict.get("href", "")
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
            self.current_company["name"] = data
            self.in_search_title = False
        elif self.current_company and self.current_company.get("name"):
            self.current_data.append(data)
    
    def handle_endtag(self, tag):
        if tag == "p" and self.current_company:
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
            
            self.current_company = None
            self.current_data = []


def search_nif_pt(query: str, page: int = 1) -> List[Dict[str, Any]]:
    """Search NIF.pt for companies"""
    url = "https://www.nif.pt/"
    params = {"q": query}
    if page > 1:
        params["page"] = page
    
    headers = {"User-Agent": config.USER_AGENT}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        parser = NIFSearchParser()
        parser.feed(response.text)
        return parser.companies
    except requests.RequestException as e:
        print(f"❌ Error searching NIF.pt: {e}")
        return []


def search_multiple_pages(query: str, max_pages: int = 10, delay: float = 2.0) -> List[Dict[str, Any]]:
    """Search multiple pages of results"""
    all_companies = []
    for page in range(1, max_pages + 1):
        companies = search_nif_pt(query, page)
        if not companies:
            break
        all_companies.extend(companies)
        if page < max_pages:
            time.sleep(delay)
    return all_companies
