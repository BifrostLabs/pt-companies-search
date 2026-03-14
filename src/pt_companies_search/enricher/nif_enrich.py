"""
NIF.pt API Enrichment Logic
"""

import json
import time
import requests
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from functools import wraps

from pt_companies_search.core.config import config
from pt_companies_search.core.database import transaction

# Rate limits (Free Tier)
LIMITS = {
    "minute": {"max": 1, "window": 60},
    "hour": {"max": 10, "window": 3600},
    "day": {"max": 100, "window": 86400},
    "month": {"max": 1000, "window": 2592000},
}

MAX_RETRIES = 3
RETRY_DELAY = 60
ENRICHMENT_TIMEOUT = 30

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Enrichment timed out")

def with_timeout(seconds):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                try:
                    result = func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                return result
            except (TimeoutError, ValueError):
                # ValueError if not in main thread or on Windows
                return func(*args, **kwargs)
        return wrapper
    return decorator

class RateLimiter:
    """Track and enforce NIF.pt API rate limits"""
    
    def __init__(self, limits_file: Optional[Path] = None):
        if limits_file is None:
            limits_file = Path(config.DATA_DIR) / "nif_rate_limits.json"
        self.limits_file = limits_file
        self.requests: List[float] = self._load()
    
    def _load(self) -> List[float]:
        if self.limits_file.exists():
            with open(self.limits_file, "r") as f:
                data = json.load(f)
                return data.get("requests", [])
        return []
    
    def _save(self):
        self.limits_file.parent.mkdir(exist_ok=True, parents=True)
        with open(self.limits_file, "w") as f:
            json.dump({
                "requests": self.requests,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)
    
    def _clean_old_requests(self):
        cutoff = time.time() - LIMITS["month"]["window"]
        self.requests = [t for t in self.requests if t > cutoff]
    
    def add_request(self):
        now = time.time()
        self._clean_old_requests()
        self.requests.append(now)
        self._save()
    
    def get_usage(self) -> Dict[str, Dict[str, int]]:
        self._clean_old_requests()
        usage = {}
        now = time.time()
        for period, cfg in LIMITS.items():
            window_start = now - cfg["window"]
            count = len([t for t in self.requests if t > window_start])
            usage[period] = {
                "used": count,
                "limit": cfg["max"],
                "remaining": max(0, cfg["max"] - count)
            }
        return usage
    
    def can_make_request(self) -> Tuple[bool, Optional[str], float]:
        self._clean_old_requests()
        now = time.time()
        for period in ["minute", "hour", "day", "month"]:
            cfg = LIMITS[period]
            window_start = now - cfg["window"]
            period_requests = [t for t in self.requests if t > window_start]
            count = len(period_requests)
            
            if count >= cfg["max"]:
                oldest = min(period_requests)
                wait_until = oldest + cfg["window"]
                wait_seconds = max(0, wait_until - now)
                return False, f"{period} limit reached", wait_seconds
        
        if self.requests:
            last_request = max(self.requests)
            elapsed = now - last_request
            if elapsed < 60:
                return False, "Minimum 60s delay", 60 - elapsed
        
        return True, None, 0


@with_timeout(ENRICHMENT_TIMEOUT)
def enrich_company(nif: str, api_key: str, rate_limiter: RateLimiter) -> Optional[Dict[str, Any]]:
    """Fetch company details from NIF.pt API"""
    url = f"http://www.nif.pt/?json=1&q={nif}&key={api_key}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=25)
            response.raise_for_status()
            rate_limiter.add_request()
            data = response.json()
            
            if data.get("result") != "success":
                return None
            
            record = data.get("records", {}).get(str(nif), {})
            if not record:
                return None
            
            # API can return nested place or top-level fields
            place = record.get("place", {})
            contacts = record.get("contacts", {})
            geo = record.get("geo", {})
            structure = record.get("structure", {})

            # Get title/name - use title field, map to name for database compatibility
            company_name = record.get("title") or record.get("alias") or ""
            
            # Get contact info
            phone = contacts.get("phone")
            email = contacts.get("email")
            website = contacts.get("website")
            fax = contacts.get("fax")
            
            enriched = {
                "nif": str(nif),
                "name": company_name,  # Use 'name' for database compatibility
                "title": company_name,  # Keep title for backwards compatibility
                "address": place.get("address") or record.get("address"),
                "city": place.get("city") or record.get("city"),
                "postal_code": f"{place.get('pc4') or record.get('pc4', '')}-{place.get('pc3') or record.get('pc3', '')}".strip("-"),
                "phone": phone,
                "email": email,
                "website": website,
                "fax": fax,
                "cae": record.get("cae"),
                "activity": record.get("activity"),
                "activity_description": record.get("activity"),  # Map to activity_description for DB
                "status": record.get("status"),
                "company_nature": structure.get("nature"),  # Use correct field name
                "nature": structure.get("nature"),  # Keep for backwards compatibility
                "capital": structure.get("capital"),
                "region": geo.get("region"),
                "county": geo.get("county"),
                "parish": geo.get("parish"),
                "enriched_at": datetime.now().isoformat(),
                "enriched_source": "nif.pt",
                "seo_url": record.get("seo_url"),
                "start_date": record.get("start_date"),
                "racius": record.get("racius"),
                "pc4": place.get("pc4") or record.get("pc4"),
                "pc3": place.get("pc3") or record.get("pc3"),
            }
            # Clean None or empty strings
            return {k: v for k, v in enriched.items() if v not in [None, "", "-"]}
            
        except (requests.RequestException, json.JSONDecodeError):
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None
    return None

def wait_for_available_slot(rate_limiter: RateLimiter, verbose: bool = True) -> bool:
    """
    Wait until we can make a request without exceeding rate limits
    
    Returns: True if can proceed, False if limits exhausted
    """
    can_proceed, reason, wait_seconds = rate_limiter.can_make_request()
    
    if can_proceed:
        return True
    
    usage = rate_limiter.get_usage()
    if usage["month"]["remaining"] == 0:
        if verbose:
            print(f"\n❌ Monthly limit exhausted ({usage['month']['used']}/{usage['month']['limit']})")
        return False
        
    if usage["day"]["remaining"] == 0:
        if verbose:
            print(f"\n⚠️ Daily limit reached. Need to wait until tomorrow.")
        return False
        
    if wait_seconds > 0:
        if verbose:
            print(f"\n⏳ Waiting {wait_seconds:.1f}s for rate limit ({reason})...")
        time.sleep(wait_seconds)
        return True
        
    return False


# Key Rotation Support
def create_key_rotator():
    """Create an API key rotator from environment variables"""
    from pt_companies_search.enricher.key_rotation import APIKeyRotator, load_api_keys
    keys = load_api_keys()
    return APIKeyRotator(keys)
