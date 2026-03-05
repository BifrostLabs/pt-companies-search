#!/usr/bin/env python3
"""
Migrate existing JSON data to PostgreSQL
"""

import json
import glob
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

from db import (
    test_connection, upsert_company, bulk_upsert_companies,
    get_contact_coverage
)

# Standard sector definitions
SECTORS = {
    "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL"],
    "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS"],
    "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO"],
    "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO"],
    "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA"],
}


def get_sector(name: str) -> str:
    """Classify company into sector"""
    name_upper = name.upper()
    for sector, keywords in SECTORS.items():
        if any(kw in name_upper for kw in keywords):
            return sector
    return "Outro"


def parse_date(date_str: str) -> str:
    """Parse date from various formats"""
    if not date_str:
        return None
    
    for fmt in ["%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def migrate_einforma_data(data_dir: Path) -> int:
    """Migrate eInforma.pt data"""
    print("\n📋 Migrating eInforma.pt data...")
    
    # Load historical data
    historical_file = data_dir / "companies_historical.json"
    if not historical_file.exists():
        print("  ⚠️  No historical data found")
        return 0
    
    with open(historical_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    companies = data.get("companies", {})
    print(f"  Found {len(companies)} companies")
    
    records = []
    for nif, company in companies.items():
        records.append({
            "nif": nif,
            "name": company.get("name"),
            "source": "einforma",
            "source_url": company.get("url"),
            "registration_date": parse_date(company.get("date")),
            "sector": get_sector(company.get("name", "")),
        })
    
    if records:
        count = bulk_upsert_companies(records)
        print(f"  ✅ Migrated {count} companies")
        return count
    
    return 0


def migrate_enriched_data(data_dir: Path) -> int:
    """Migrate enriched NIF.pt API data"""
    print("\n📊 Migrating enriched data...")
    
    enriched_file = data_dir / "companies_enriched.json"
    if not enriched_file.exists():
        print("  ⚠️  No enriched data found")
        return 0
    
    with open(enriched_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    companies = data.get("companies", {})
    print(f"  Found {len(companies)} enriched companies")
    
    count = 0
    for nif, enriched in companies.items():
        # Handle CAE as list or string
        cae = enriched.get("cae")
        if isinstance(cae, list):
            cae = ", ".join(cae)[:20]  # Truncate to fit column
        
        record = {
            "nif": nif,
            "name": enriched.get("name") or enriched.get("title"),
            "source": "nif_api",
            "source_url": None,
            "registration_date": None,
            "phone": enriched.get("phone"),
            "email": enriched.get("email"),
            "website": enriched.get("website"),
            "address": enriched.get("address"),
            "city": enriched.get("city"),
            "postal_code": enriched.get("postal_code"),
            "region": enriched.get("region"),
            "county": enriched.get("county"),
            "parish": enriched.get("parish"),
            "cae": cae,
            "activity_description": enriched.get("activity"),
            "status": enriched.get("status"),
            "sector": get_sector(enriched.get("name", "")),
            "enriched_at": datetime.now().isoformat(),
        }
        
        if upsert_company(record):
            count += 1
    
    print(f"  ✅ Migrated {count} enriched companies")
    return count


def migrate_search_results(data_dir: Path) -> int:
    """Migrate NIF.pt search results"""
    print("\n🔍 Migrating search results...")
    
    search_files = sorted(glob.glob(str(data_dir / "nif_search_*.json")), reverse=True)
    if not search_files:
        print("  ⚠️  No search results found")
        return 0
    
    all_companies = []
    for search_file in search_files:
        with open(search_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_companies.extend(data.get("companies", []))
    
    # Remove duplicates
    unique = {c["nif"]: c for c in all_companies if c.get("nif")}
    print(f"  Found {len(unique)} unique companies from search")
    
    records = []
    for nif, company in unique.items():
        location = company.get("location", "")
        city = ""
        postal_code = ""
        
        if location and location != "N/A":
            parts = location.split(maxsplit=1)
            postal_code = parts[0] if parts else ""
            city = parts[1] if len(parts) > 1 else ""
        
        records.append({
            "nif": nif,
            "name": company.get("name"),
            "source": "nif_search",
            "source_url": company.get("url"),
            "city": city,
            "postal_code": postal_code,
            "sector": get_sector(company.get("name", "")),
        })
    
    if records:
        count = bulk_upsert_companies(records)
        print(f"  ✅ Migrated {count} search results")
        return count
    
    return 0


def main():
    print("=" * 60)
    print("PT Companies - PostgreSQL Migration")
    print("=" * 60)
    
    # Test connection
    if not test_connection():
        print("\n❌ Cannot connect to database")
        print("\nMake sure PostgreSQL is running:")
        print("  docker-compose -f docker-compose.postgres.yml up -d")
        return
    
    print("✅ Database connection successful\n")
    
    data_dir = Path(__file__).parent / "data"
    
    # Migrate all data sources
    total = 0
    total += migrate_einforma_data(data_dir)
    total += migrate_enriched_data(data_dir)
    total += migrate_search_results(data_dir)
    
    # Show final stats
    print("\n" + "=" * 60)
    print("Migration Complete!")
    print("=" * 60)
    print(f"Total records processed: {total}")
    
    # Show database stats
    stats = get_contact_coverage()
    print(f"\nDatabase Statistics:")
    print(f"  Total companies: {stats.get('total', 0)}")
    print(f"  With phone: {stats.get('with_phone', 0)}")
    print(f"  With email: {stats.get('with_email', 0)}")
    print(f"  With website: {stats.get('with_website', 0)}")


if __name__ == "__main__":
    main()
