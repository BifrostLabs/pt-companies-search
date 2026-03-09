#!/usr/bin/env python3
"""
Database Enrichment Sync Tool
Sync enriched data between JSON and PostgreSQL
"""

import argparse
from pathlib import Path
import json
from datetime import datetime

from db import get_cursor, test_connection
from db_loader import is_db_available


def get_json_enriched() -> dict:
    """Load enriched companies from JSON"""
    enriched_file = Path(__file__).parent / "data" / "companies_enriched.json"
    if enriched_file.exists():
        with open(enriched_file, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("companies", {})
    return {}


def get_db_stats() -> dict:
    """Get enrichment statistics from database"""
    if not is_db_available():
        return {"total": 0, "enriched": 0, "with_contact": 0}
    
    with get_cursor() as cur:
        cur.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(enriched_at) as enriched,
                COUNT(CASE WHEN phone IS NOT NULL OR email IS NOT NULL THEN 1 END) as with_contact
            FROM companies
        """)
        return dict(cur.fetchone())


def sync_json_to_db(dry_run: bool = False) -> int:
    """
    Sync enriched companies from JSON to PostgreSQL
    
    Returns: Number of companies synced
    """
    if not is_db_available():
        print("❌ PostgreSQL not available")
        return 0
    
    json_companies = get_json_enriched()
    if not json_companies:
        print("ℹ️  No enriched companies in JSON")
        return 0
    
    print(f"📋 Found {len(json_companies)} enriched companies in JSON")
    
    if dry_run:
        print("\n🔍 DRY RUN - Would sync these companies:")
        for nif, data in list(json_companies.items())[:5]:
            name = data.get("name") or data.get("title", "Unknown")
            print(f"   {nif}: {name}")
        if len(json_companies) > 5:
            print(f"   ... and {len(json_companies) - 5} more")
        return 0
    
    synced = 0
    with get_cursor() as cur:
        for nif, data in json_companies.items():
            # Handle CAE as list or string
            cae = data.get("cae")
            if isinstance(cae, list):
                cae = ", ".join(str(c) for c in cae)[:20] if cae else None
            
            try:
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
                synced += 1
            except Exception as e:
                print(f"❌ Error syncing {nif}: {e}")
    
    return synced


def get_sector(name: str) -> str:
    """Extract sector from company name"""
    name_lower = name.lower()
    
    sectors = {
        "tecnologia": ["tech", "software", "informática", "digital", "sistemas", "computadores"],
        "construção": ["construção", "construcao", "obra", "engenharia", "civil"],
        "restauração": ["restaurante", "café", "bar", "pastelaria", "food"],
        "comércio": ["comércio", "comercio", "loja", "store", "varejo"],
        "serviços": ["serviços", "servicos", "consulting", "consultoria"],
        "saúde": ["saúde", "saude", "clínica", "clinica", "médico", "medico"],
        "educação": ["educação", "educacao", "escola", "formação", "formacao"],
        "imobiliária": ["imobiliária", "imobiliaria", "imóveis", "imoveis"],
        "transportes": ["transporte", "logística", "logistica"],
        "turismo": ["turismo", "hotel", "viagens", "travel"],
    }
    
    for sector, keywords in sectors.items():
        if any(kw in name_lower for kw in keywords):
            return sector
    
    return "outros"


def show_status():
    """Show enrichment status for both JSON and DB"""
    print("📊 Enrichment Status\n")
    
    # JSON stats
    json_companies = get_json_enriched()
    print(f"📁 JSON File:")
    print(f"   Enriched: {len(json_companies)}")
    
    # DB stats
    print(f"\n🗄️  PostgreSQL:")
    if is_db_available():
        stats = get_db_stats()
        print(f"   Total companies: {stats['total']}")
        print(f"   Enriched: {stats['enriched']}")
        print(f"   With contact: {stats['with_contact']}")
    else:
        print("   ❌ Not available")
    
    # Sync status
    if json_companies and is_db_available():
        stats = get_db_stats()
        if len(json_companies) != stats['enriched']:
            print(f"\n⚠️  Sync needed: JSON has {len(json_companies)}, DB has {stats['enriched']}")
        else:
            print(f"\n✅ In sync")


def main():
    parser = argparse.ArgumentParser(description="Sync enriched data between JSON and PostgreSQL")
    parser.add_argument("--status", action="store_true", help="Show enrichment status")
    parser.add_argument("--sync", action="store_true", help="Sync JSON enrichments to DB")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be synced without doing it")
    args = parser.parse_args()
    
    # Default to status if no args
    if not (args.status or args.sync or args.dry_run):
        args.status = True
    
    if args.status:
        show_status()
    
    if args.sync or args.dry_run:
        print("\n🔄 Syncing JSON enrichments to PostgreSQL...")
        count = sync_json_to_db(dry_run=args.dry_run)
        if not args.dry_run and count > 0:
            print(f"✅ Synced {count} companies to PostgreSQL")


if __name__ == "__main__":
    main()
