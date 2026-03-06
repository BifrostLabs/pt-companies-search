#!/usr/bin/env python3
"""
Sync all search results from JSON to PostgreSQL
Handles duplicates by using UPSERT (ON CONFLICT)
"""

import json
import glob
from pathlib import Path
from datetime import datetime
from db import get_cursor

DATA_DIR = Path(__file__).parent / "data"


def sync_search_results():
    """Sync all search results from JSON files to database"""
    
    # Find all search files
    search_files = sorted(glob.glob(str(DATA_DIR / "nif_search_*.json")))
    
    if not search_files:
        print("❌ No search files found")
        return
    
    print(f"📁 Found {len(search_files)} search files")
    
    # Load all companies
    all_companies = {}
    for search_file in search_files:
        with open(search_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            companies = data.get("companies", [])
            
            for company in companies:
                nif = company.get("nif")
                if nif and nif not in all_companies:
                    all_companies[nif] = company
    
    print(f"📊 Total unique companies: {len(all_companies)}")
    
    # Sync to database
    print("\n🔄 Syncing to PostgreSQL...")
    
    with get_cursor() as cur:
        inserted = 0
        skipped = 0
        
        for nif, company in all_companies.items():
            try:
                # Parse location
                location = company.get("location", "")
                city = company.get("city", "")
                postal_code = company.get("postal_code", "")
                
                if location and not city:
                    parts = location.split(maxsplit=1)
                    if len(parts) > 1:
                        postal_code = parts[0]
                        city = parts[1]
                
                # Get sector
                name = company.get("name", "")
                sector = get_sector(name)
                
                cur.execute("""
                    INSERT INTO companies (
                        nif, name, source, source_url, city, postal_code, sector
                    ) VALUES (
                        %s, %s, 'nif_search', %s, %s, %s, %s
                    )
                    ON CONFLICT (nif) DO UPDATE SET
                        name = COALESCE(EXCLUDED.name, companies.name),
                        source_url = COALESCE(EXCLUDED.source_url, companies.source_url),
                        city = COALESCE(EXCLUDED.city, companies.city),
                        postal_code = COALESCE(EXCLUDED.postal_code, companies.postal_code),
                        sector = COALESCE(EXCLUDED.sector, companies.sector),
                        fetched_at = NOW()
                """, (
                    nif,
                    name,
                    company.get("url", f"https://www.nif.pt/{nif}/"),
                    city,
                    postal_code,
                    sector
                ))
                inserted += 1
                
            except Exception as e:
                print(f"  ❌ Error syncing {nif}: {e}")
                skipped += 1
    
    print(f"✅ Synced {inserted} companies to PostgreSQL")
    if skipped > 0:
        print(f"⚠️  Skipped {skipped} due to errors")
    
    # Verify
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) as count FROM companies WHERE source = 'nif_search'")
        result = cur.fetchone()
        count = result['count'] if result else 0
        print(f"\n📊 Total search results in DB: {count}")


def get_sector(name: str) -> str:
    """Classify company into sector"""
    if not name:
        return "Outro"
    
    sectors = {
        "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL"],
        "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS"],
        "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO"],
        "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO"],
        "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA"],
    }
    
    name_upper = name.upper()
    for sector, keywords in sectors.items():
        if any(kw in name_upper for kw in keywords):
            return sector
    
    return "Outro"


if __name__ == "__main__":
    sync_search_results()
