#!/usr/bin/env python3
"""
NIF.pt API Enrichment Script
Enriches company data with address, phone, email, website, etc.

Rate Limits (Free Tier):
- 1,000 / Month (30 days)
- 100 / Day (24 hours)
- 10 / Hour
- 1 / Minute

Timeout Handling:
- 30 second timeout per NIF enrichment
- Skips stuck NIFs and continues
- Logs timeouts to nif_timeouts.json for retry
"""

import json
import time
import requests
import signal
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from collections import defaultdict
from functools import wraps

DATA_DIR = Path(__file__).parent / "data"
CONFIG_FILE = Path(__file__).parent / "nif_config.json"
RATE_LIMIT_FILE = Path(__file__).parent / "nif_rate_limits.json"
TIMEOUT_LOG_FILE = Path(__file__).parent / "nif_timeouts.json"

# Rate limits (Free Tier)
LIMITS = {
    "minute": {"max": 1, "window": 60},           # 1 per minute
    "hour": {"max": 10, "window": 3600},          # 10 per hour
    "day": {"max": 100, "window": 86400},         # 100 per day
    "month": {"max": 1000, "window": 2592000},    # 1000 per 30 days
}

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 60  # seconds to wait after network error
ENRICHMENT_TIMEOUT = 30  # seconds per NIF enrichment


class TimeoutError(Exception):
    """Custom timeout exception"""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout"""
    raise TimeoutError("Enrichment timed out")


def with_timeout(seconds):
    """
    Decorator to add timeout to a function (Unix/Linux only)
    Falls back gracefully on Windows
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Try signal-based timeout (Unix/Linux)
            try:
                # Set signal handler
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                
                try:
                    result = func(*args, **kwargs)
                finally:
                    # Cancel alarm and restore old handler
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)
                
                return result
                
            except TimeoutError:
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")
            except ValueError:
                # Signal not available (Windows), fall back to no timeout
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


class RateLimiter:
    """Track and enforce NIF.pt API rate limits"""
    
    def __init__(self, limits_file: Path = RATE_LIMIT_FILE):
        self.limits_file = limits_file
        self.requests: List[float] = self._load()
    
    def _load(self) -> List[float]:
        """Load request timestamps from file"""
        if self.limits_file.exists():
            with open(self.limits_file, "r") as f:
                data = json.load(f)
                # Migrate from old format if needed
                if isinstance(data.get("requests"), dict):
                    # Old format - take the longest list (month)
                    all_requests = []
                    for period_requests in data["requests"].values():
                        all_requests.extend(period_requests)
                    return list(set(all_requests))  # Deduplicate
                return data.get("requests", [])
        return []
    
    def _save(self):
        """Save request timestamps to file"""
        self.limits_file.parent.mkdir(exist_ok=True)
        with open(self.limits_file, "w") as f:
            json.dump({
                "requests": self.requests,
                "last_updated": datetime.now().isoformat()
            }, f, indent=2)
    
    def _clean_old_requests(self):
        """Remove timestamps older than the longest window (30 days)"""
        cutoff = time.time() - LIMITS["month"]["window"]
        self.requests = [t for t in self.requests if t > cutoff]
    
    def add_request(self):
        """Record a new API request"""
        now = time.time()
        self._clean_old_requests()
        
        # Add single timestamp
        self.requests.append(now)
        self._save()
    
    def get_usage(self) -> Dict[str, Dict[str, int]]:
        """Get current usage for all periods"""
        self._clean_old_requests()
        
        usage = {}
        for period, config in LIMITS.items():
            window_start = time.time() - config["window"]
            count = len([t for t in self.requests if t > window_start])
            usage[period] = {
                "used": count,
                "limit": config["max"],
                "remaining": max(0, config["max"] - count)
            }
        
        return usage
    
    def can_make_request(self) -> tuple[bool, Optional[str], float]:
        """
        Check if we can make a request without exceeding limits
        
        Returns: (can_proceed, reason_if_blocked, wait_seconds)
        """
        self._clean_old_requests()
        usage = self.get_usage()
        
        # Check each limit (most restrictive first)
        for period in ["minute", "hour", "day", "month"]:
            config = LIMITS[period]
            window_start = time.time() - config["window"]
            count = len([t for t in self.requests if t > window_start])
            
            if count >= config["max"]:
                # Calculate wait time until oldest request expires
                period_requests = [t for t in self.requests if t > window_start]
                if period_requests:
                    oldest = min(period_requests)
                    wait_until = oldest + config["window"]
                    wait_seconds = max(0, wait_until - time.time())
                else:
                    wait_seconds = config["window"]
                
                period_names = {
                    "minute": "1 per minute",
                    "hour": "10 per hour",
                    "day": "100 per day",
                    "month": "1000 per month"
                }
                
                return False, f"{period_names[period]} limit reached ({count}/{config['max']})", wait_seconds
        
        # Check minimum delay (1 per minute = 60s between requests)
        if self.requests:
            last_request = max(self.requests)
            elapsed = time.time() - last_request
            min_delay = 60  # 1 per minute = 60s minimum
            
            if elapsed < min_delay:
                wait_seconds = min_delay - elapsed
                return False, "Minimum 60s between requests", wait_seconds
        
        return True, None, 0
    
    def display_status(self):
        """Display current rate limit status"""
        usage = self.get_usage()
        
        print("\n📊 Rate Limit Status:")
        print(f"   Minute: {usage['minute']['used']:2d}/{usage['minute']['limit']:4d} ({usage['minute']['remaining']} remaining)")
        print(f"   Hour:   {usage['hour']['used']:2d}/{usage['hour']['limit']:4d} ({usage['hour']['remaining']} remaining)")
        print(f"   Day:    {usage['day']['used']:3d}/{usage['day']['limit']:4d} ({usage['day']['remaining']} remaining)")
        print(f"   Month:  {usage['month']['used']:4d}/{usage['month']['limit']:4d} ({usage['month']['remaining']} remaining)")


def load_config() -> dict:
    """Load NIF.pt API configuration"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"api_key": "", "last_run": None, "credits_used": 0}


def save_config(config: dict):
    """Save configuration"""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def load_timeout_log() -> dict:
    """Load log of timed out NIFs"""
    if TIMEOUT_LOG_FILE.exists():
        with open(TIMEOUT_LOG_FILE, "r") as f:
            return json.load(f)
    return {"timeouts": {}, "last_updated": None}


def save_timeout_log(data: dict):
    """Save timeout log"""
    data["last_updated"] = datetime.now().isoformat()
    with open(TIMEOUT_LOG_FILE, "w") as f:
        json.dump(data, f, indent=2)


def log_timeout(nif: str, company_name: str = ""):
    """Log a timed out NIF for later retry"""
    log = load_timeout_log()
    log["timeouts"][nif] = {
        "name": company_name,
        "timestamp": datetime.now().isoformat(),
        "retry_count": log["timeouts"].get(nif, {}).get("retry_count", 0) + 1
    }
    save_timeout_log(log)


def is_recently_timed_out(nif: str, hours: int = 24) -> bool:
    """Check if NIF timed out recently (within specified hours)"""
    log = load_timeout_log()
    if nif not in log["timeouts"]:
        return False
    
    timeout_time = datetime.fromisoformat(log["timeouts"][nif]["timestamp"])
    return datetime.now() - timeout_time < timedelta(hours=hours)


@with_timeout(ENRICHMENT_TIMEOUT)
def enrich_company(nif: str, api_key: str, rate_limiter: RateLimiter, company_name: str = "") -> Optional[Dict[str, Any]]:
    """
    Fetch company details from NIF.pt API
    
    Returns enriched data or None if failed
    
    Timeout: 30 seconds per NIF
    """
    url = f"http://www.nif.pt/?json=1&q={nif}&key={api_key}"
    
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.get(url, timeout=25)  # Slightly less than overall timeout
            response.raise_for_status()
            
            # Record this request for rate limiting
            rate_limiter.add_request()
            
            data = response.json()
            
            if data.get("result") != "success":
                print(f"   ⚠️  No data for NIF {nif}")
                return None
            
            record = data.get("records", {}).get(str(nif), {})
            
            if not record:
                print(f"   ⚠️  Empty record for NIF {nif}")
                return None
            
            # Extract enriched data
            enriched = {
                "nif": nif,
                "title": record.get("title"),
                "seo_url": record.get("seo_url"),
                "alias": record.get("alias"),
                "address": record.get("place", {}).get("address"),
                "city": record.get("place", {}).get("city"),
                "postal_code": f"{record.get('place', {}).get('pc4', '')}-{record.get('place', {}).get('pc3', '')}".rstrip("-"),
                "phone": record.get("contacts", {}).get("phone"),
                "email": record.get("contacts", {}).get("email"),
                "website": record.get("contacts", {}).get("website"),
                "fax": record.get("contacts", {}).get("fax"),
                "cae": record.get("cae"),
                "activity": record.get("activity"),
                "status": record.get("status"),
                "nature": record.get("structure", {}).get("nature"),
                "capital": record.get("structure", {}).get("capital"),
                "capital_currency": record.get("structure", {}).get("capital_currency"),
                "region": record.get("geo", {}).get("region"),
                "county": record.get("geo", {}).get("county"),
                "parish": record.get("geo", {}).get("parish"),
                "racius_url": record.get("racius"),
                "portugalio_url": record.get("portugalio"),
                "enriched_at": datetime.now().isoformat(),
                "enriched_source": "nif.pt"
            }
            
            # Remove None values
            enriched = {k: v for k, v in enriched.items() if v is not None}
            
            return enriched
            
        except requests.exceptions.ConnectionError as e:
            print(f"   ❌ Network error for NIF {nif} (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                print(f"   ⏳ Waiting {RETRY_DELAY}s before retry...")
                time.sleep(RETRY_DELAY)
            else:
                print(f"   ❌ Max retries reached for NIF {nif}")
                return None
                
        except requests.exceptions.Timeout as e:
            print(f"   ⏱️  Timeout for NIF {nif} (attempt {attempt + 1}/{MAX_RETRIES})")
            if attempt < MAX_RETRIES - 1:
                print(f"   ⏳ Waiting {RETRY_DELAY}s before retry...")
                time.sleep(RETRY_DELAY)
            else:
                return None
                
        except requests.RequestException as e:
            print(f"   ❌ Request error for NIF {nif}: {e}")
            return None
            
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON decode error for NIF {nif}: {e}")
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
    
    # Check if we've hit the monthly limit
    usage = rate_limiter.get_usage()
    if usage["month"]["remaining"] == 0:
        if verbose:
            print(f"\n❌ Monthly limit exhausted ({usage['month']['used']}/{usage['month']['limit']})")
            print("   Please wait for the 30-day window to reset or upgrade your plan.")
        return False
    
    # Wait for the required time
    if verbose:
        if wait_seconds > 60:
            mins = int(wait_seconds // 60)
            secs = int(wait_seconds % 60)
            print(f"\n⏳ {reason}. Waiting {mins}m {secs}s...")
        else:
            print(f"\n⏳ {reason}. Waiting {int(wait_seconds)}s...")
    
    time.sleep(wait_seconds + 1)  # Add 1s buffer
    
    return True


def estimate_completion(rate_limiter: RateLimiter, remaining_count: int) -> Optional[datetime]:
    """
    Estimate completion time based on rate limits
    
    Returns: Estimated completion datetime or None if can't estimate
    """
    usage = rate_limiter.get_usage()
    
    # Check if we have enough monthly quota
    if remaining_count > usage["month"]["remaining"]:
        return None  # Can't complete with current quota
    
    # At 1 request per minute, calculate time
    minutes_needed = remaining_count * 1  # 1 min per request
    
    return datetime.now() + timedelta(minutes=minutes_needed)


def load_companies_to_enrich(source: str = "historical") -> list:
    """
    Load companies that need enrichment
    
    Args:
        source: "historical" for all historical data, "latest" for latest snapshot
    """
    if source == "historical":
        historical_file = DATA_DIR / "companies_historical.json"
        if historical_file.exists():
            with open(historical_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return list(data.get("companies", {}).values())
    else:
        # Find latest snapshot
        import glob
        files = sorted(glob.glob(str(DATA_DIR / "companies_*.json")), reverse=True)
        files = [f for f in files if "_enriched" not in f and "_historical" not in f]
        if files:
            with open(files[0], "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("companies", [])
    
    return []


def load_enriched_data() -> dict:
    """Load previously enriched data"""
    enriched_file = DATA_DIR / "companies_enriched.json"
    if enriched_file.exists():
        with open(enriched_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"companies": {}, "metadata": {"last_updated": None, "total_enriched": 0}}


def save_enriched_data(data: dict):
    """Save enriched data to JSON and database"""
    enriched_file = DATA_DIR / "companies_enriched.json"
    enriched_file.parent.mkdir(exist_ok=True)
    
    data["metadata"]["last_updated"] = datetime.now().isoformat()
    data["metadata"]["total_enriched"] = len(data["companies"])
    
    # Save to JSON
    with open(enriched_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # Also save to database
    save_enriched_to_db(data["companies"])


def save_enriched_to_db(companies: dict):
    """Save enriched companies to PostgreSQL"""
    try:
        from db import get_connection
        
        count = 0
        with get_connection() as conn:
            with conn.cursor() as cur:
                for nif, data in companies.items():
                    # Handle CAE as list or string
                    cae = data.get("cae")
                    if isinstance(cae, list):
                        cae = ", ".join(str(c) for c in cae)[:20] if cae else None
                    
                    cur.execute("""
                        INSERT INTO companies (
                            nif, name, source, phone, email, website, fax,
                            address, city, postal_code, region, county, parish,
                            cae, activity_description, status, sector,
                            company_nature, capital, enriched_at
                        ) VALUES (
                            %s, %s, 'nif_api', %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, NOW()
                        )
                        ON CONFLICT (nif) DO UPDATE SET
                            name = COALESCE(EXCLUDED.name, companies.name),
                            phone = EXCLUDED.phone,
                            email = EXCLUDED.email,
                            website = EXCLUDED.website,
                            fax = EXCLUDED.fax,
                            address = COALESCE(EXCLUDED.address, companies.address),
                            city = COALESCE(EXCLUDED.city, companies.city),
                            postal_code = COALESCE(EXCLUDED.postal_code, companies.postal_code),
                            region = COALESCE(EXCLUDED.region, companies.region),
                            county = COALESCE(EXCLUDED.county, companies.county),
                            parish = COALESCE(EXCLUDED.parish, companies.parish),
                            cae = COALESCE(EXCLUDED.cae, companies.cae),
                            activity_description = COALESCE(EXCLUDED.activity_description, companies.activity_description),
                            status = COALESCE(EXCLUDED.status, companies.status),
                            sector = COALESCE(EXCLUDED.sector, companies.sector),
                            company_nature = COALESCE(EXCLUDED.company_nature, companies.company_nature),
                            capital = COALESCE(EXCLUDED.capital, companies.capital),
                            enriched_at = NOW(),
                            last_verified_at = NOW()
                    """, (
                        nif,
                        data.get("name") or data.get("title"),
                        data.get("phone"),
                        data.get("email"),
                        data.get("website"),
                        data.get("fax"),
                        data.get("address"),
                        data.get("city"),
                        data.get("postal_code"),
                        data.get("region"),
                        data.get("county"),
                        data.get("parish"),
                        cae,
                        data.get("activity"),
                        data.get("status"),
                        get_sector(data.get("name") or data.get("title", "")),
                        data.get("nature"),
                        data.get("capital"),
                    ))
                    count += 1
        
        if count > 0:
            print(f"🗄️  Saved {count} companies to PostgreSQL")
        
    except Exception as e:
        # Don't fail if DB is not available
        pass


def merge_enriched_data(company: dict, enriched: dict) -> dict:
    """Merge original company data with enriched data"""
    merged = {**company}
    
    # Add enriched fields (don't overwrite original NIF, name, date, url)
    for key, value in enriched.items():
        if key not in ["nif"] and value is not None:
            merged[key] = value
    
    return merged


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Enrich company data from NIF.pt API")
    parser.add_argument("--source", choices=["historical", "latest"], default="historical",
                        help="Data source to enrich")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of companies to enrich (0 = all)")
    parser.add_argument("--force", action="store_true",
                        help="Re-enrich already enriched companies")
    parser.add_argument("--nif", type=str,
                        help="Enrich specific NIF only")
    parser.add_argument("--setup", action="store_true",
                        help="Setup API key")
    parser.add_argument("--status", action="store_true",
                        help="Show rate limit status only")
    parser.add_argument("--reset", action="store_true",
                        help="Reset rate limit tracking")
    parser.add_argument("--show-timeouts", action="store_true",
                        help="Show timed out NIFs")
    parser.add_argument("--retry-timeouts", action="store_true",
                        help="Retry timed out NIFs (ignores 24h skip)")
    parser.add_argument("--clear-timeouts", action="store_true",
                        help="Clear timeout log")
    args = parser.parse_args()
    
    # Clear timeout log
    if args.clear_timeouts:
        print("🗑️  Clearing timeout log...")
        if TIMEOUT_LOG_FILE.exists():
            TIMEOUT_LOG_FILE.unlink()
            print("✅ Timeout log cleared")
        else:
            print("ℹ️  No timeout log to clear")
        return
    
    # Show timeouts
    if args.show_timeouts:
        print("⏱️  Timed Out NIFs\n")
        log = load_timeout_log()
        if not log["timeouts"]:
            print("   No timeouts recorded")
        else:
            for nif, info in log["timeouts"].items():
                timestamp = info["timestamp"][:19]
                retry_count = info.get("retry_count", 0)
                name = info.get("name", "Unknown")[:40]
                print(f"   {nif} | {timestamp} | retries: {retry_count} | {name}")
        print(f"\n   Total: {len(log['timeouts'])} timed out NIFs")
        return
    
    # Reset mode
    if args.reset:
        print("🔄 Resetting rate limit tracking...")
        if RATE_LIMIT_FILE.exists():
            RATE_LIMIT_FILE.unlink()
            print("✅ Rate limits reset")
        else:
            print("ℹ️  No rate limit file to reset")
        return
    
    # Status mode
    if args.status:
        print("📊 NIF.pt API Rate Limit Status\n")
        rate_limiter = RateLimiter()
        rate_limiter.display_status()
        
        # Show enriched data stats
        enriched_data = load_enriched_data()
        print(f"\n📈 Enrichment Progress:")
        print(f"   Total enriched: {len(enriched_data['companies'])}")
        if enriched_data["metadata"].get("last_updated"):
            print(f"   Last run: {enriched_data['metadata']['last_updated'][:19]}")
        return
    
    # Setup mode
    if args.setup:
        print("🔑 NIF.pt API Setup")
        print("\nTo use this script, you need an API key from NIF.pt")
        print("Request a key at: http://www.nif.pt/contactos/api/")
        print()
        
        config = load_config()
        api_key = input("Enter your NIF.pt API key: ").strip()
        
        if api_key:
            config["api_key"] = api_key
            save_config(config)
            print("✅ API key saved!")
        return
    
    # Load config
    config = load_config()
    
    if not config.get("api_key"):
        print("❌ No API key configured. Run with --setup first.")
        return
    
    api_key = config["api_key"]
    
    # Single NIF mode
    if args.nif:
        print(f"🔍 Enriching NIF {args.nif}...")
        rate_limiter = RateLimiter()
        rate_limiter.display_status()
        
        # Wait for available slot
        if not wait_for_available_slot(rate_limiter):
            return
        
        enriched = enrich_company(args.nif, api_key, rate_limiter)
        
        if enriched:
            # Save to enriched file
            enriched_data = load_enriched_data()
            enriched_data["companies"][args.nif] = enriched
            save_enriched_data(enriched_data)
            
            print(f"\n✅ Enriched data:")
            for key, value in enriched.items():
                if value:
                    print(f"   {key}: {value}")
            print(f"\n💾 Saved to: {DATA_DIR / 'companies_enriched.json'}")
        
        rate_limiter.display_status()
        return
    
    # Initialize rate limiter
    rate_limiter = RateLimiter()
    rate_limiter.display_status()
    
    # Check if we have any quota left
    usage = rate_limiter.get_usage()
    if usage["month"]["remaining"] == 0:
        print("\n❌ Monthly API limit exhausted. Please wait for the 30-day window to reset.")
        return
    
    # Load companies to enrich
    print(f"📂 Loading companies from {args.source}...")
    companies = load_companies_to_enrich(args.source)
    
    if not companies:
        print("❌ No companies found to enrich")
        return
    
    print(f"   Found {len(companies)} companies")
    
    # Load already enriched data
    enriched_data = load_enriched_data()
    already_enriched = set(enriched_data["companies"].keys())
    
    # Filter out already enriched (unless force)
    if not args.force:
        to_enrich = [c for c in companies if c["nif"] not in already_enriched]
        print(f"   Already enriched: {len(already_enriched)}")
        print(f"   To enrich: {len(to_enrich)}")
    else:
        to_enrich = companies
        print(f"   Force mode: enriching all {len(to_enrich)} companies")
    
    # Apply limit
    if args.limit > 0:
        to_enrich = to_enrich[:args.limit]
        print(f"   Limited to: {len(to_enrich)} companies")
    
    if not to_enrich:
        print("✅ Nothing to enrich")
        return
    
    # Check if we have enough quota
    if len(to_enrich) > usage["month"]["remaining"]:
        print(f"\n⚠️  Warning: Not enough monthly quota for all {len(to_enrich)} companies")
        print(f"   Will enrich {usage['month']['remaining']} companies and stop.")
    
    # Estimate completion time
    estimated_completion = estimate_completion(rate_limiter, len(to_enrich))
    if estimated_completion:
        print(f"\n⏱️  Estimated completion: {estimated_completion.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   (at 1 request per minute rate limit)")
    
    # Enrich companies
    print(f"\n🚀 Starting enrichment...")
    
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    for i, company in enumerate(to_enrich, 1):
        nif = company["nif"]
        name = company.get("name", "Unknown")[:40]
        
        # Skip if recently timed out (unless retry mode)
        if not args.retry_timeouts and is_recently_timed_out(nif, hours=24):
            print(f"\n[{i}/{len(to_enrich)}] {nif} - {name}...")
            print(f"   ⏭️  Skipping (timed out in last 24h)")
            fail_count += 1
            continue
        
        # Wait for available slot (respects rate limits)
        if not wait_for_available_slot(rate_limiter):
            print(f"\n❌ Rate limit exhausted. Stopping at {i-1}/{len(to_enrich)}")
            break
        
        print(f"\n[{i}/{len(to_enrich)}] {nif} - {name}...")
        
        try:
            enriched = enrich_company(nif, api_key, rate_limiter, company_name=name)
            
            if enriched:
                # Merge with original data
                merged = merge_enriched_data(company, enriched)
                enriched_data["companies"][nif] = merged
                success_count += 1
                
                # Show key enriched fields
                if enriched.get("address"):
                    print(f"   📍 {enriched.get('address')}, {enriched.get('city', '')}")
                if enriched.get("phone"):
                    print(f"   📞 {enriched.get('phone')}")
                if enriched.get("email"):
                    print(f"   ✉️  {enriched.get('email')}")
            else:
                fail_count += 1
                
        except TimeoutError as e:
            print(f"   ⏱️  TIMEOUT after {ENRICHMENT_TIMEOUT}s - skipping")
            log_timeout(nif, name)
            fail_count += 1
            continue
        
        # Save progress every 10 companies
        if i % 10 == 0:
            save_enriched_data(enriched_data)
            rate_limiter.display_status()
    
    # Final save
    save_enriched_data(enriched_data)
    
    # Update config
    config["last_run"] = datetime.now().isoformat()
    config["credits_used"] = config.get("credits_used", 0) + success_count
    save_config(config)
    
    # Summary
    print(f"\n{'='*50}")
    print(f"📊 Enrichment Summary")
    print(f"{'='*50}")
    print(f"   ✅ Success: {success_count}")
    print(f"   ❌ Failed: {fail_count}")
    print(f"   📊 Total enriched: {len(enriched_data['companies'])}")
    print(f"   💾 Saved to: {DATA_DIR / 'companies_enriched.json'}")
    
    # Final rate limit status
    rate_limiter.display_status()


if __name__ == "__main__":
    main()
