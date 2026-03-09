#!/usr/bin/env python3
"""
Database loader for Streamlit dashboard
Automatically uses PostgreSQL when available, falls back to JSON
"""

import json
import glob
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd

# Try to import database module
DB_AVAILABLE = False
try:
    from db import test_connection, get_connection
    DB_AVAILABLE = test_connection()
except ImportError:
    pass

DATA_DIR = Path(__file__).parent / "data"


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


# ==================== JSON LOADERS (FALLBACK) ====================

def load_json_enriched() -> Dict:
    """Load enriched data from JSON"""
    enriched_file = DATA_DIR / "companies_enriched.json"
    if enriched_file.exists():
        with open(enriched_file, "r", encoding="utf-8") as f:
            return json.load(f).get("companies", {})
    return {}


def load_json_search() -> List[Dict]:
    """Load search results from JSON files"""
    search_files = sorted(glob.glob(str(DATA_DIR / "nif_search_*.json")), reverse=True)
    if not search_files:
        return []
    
    all_companies = []
    for search_file in search_files:
        with open(search_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_companies.extend(data.get("companies", []))
    
    # Remove duplicates
    unique = {}
    for c in all_companies:
        nif = c.get("nif")
        if nif and nif not in unique:
            unique[nif] = c
    
    return list(unique.values())


def load_json_einforma() -> Dict:
    """Load eInforma historical data from JSON"""
    hist_file = DATA_DIR / "companies_historical.json"
    if hist_file.exists():
        with open(hist_file, "r", encoding="utf-8") as f:
            return json.load(f).get("companies", {})
    return {}


# ==================== UNIFIED LOADERS ====================

@st.cache_data(ttl=3600)
def get_enriched_dataframe() -> pd.DataFrame:
    """Get enriched companies as DataFrame (from DB or JSON)"""
    if DB_AVAILABLE:
        # Use database
        try:
            from db import get_connection
            with get_connection() as conn:
                df = pd.read_sql("""
                    SELECT nif, name, phone, email, website, address, 
                           city, postal_code, region, county, parish,
                           cae, activity_description, status, sector
                    FROM companies 
                    WHERE source = 'nif_api'
                    ORDER BY enriched_at DESC NULLS LAST
                """, conn)
                return df
        except Exception as e:
            print(f"DB error, falling back to JSON: {e}")
    
    # Fallback to JSON
    enriched_data = load_json_enriched()
    if not enriched_data:
        return pd.DataFrame()
    
    rows = []
    for nif, data in enriched_data.items():
        rows.append({
            "nif": nif,
            "name": data.get("name") or data.get("title", "Unknown"),
            "phone": data.get("phone"),
            "email": data.get("email"),
            "website": data.get("website"),
            "address": data.get("address"),
            "city": data.get("city"),
            "postal_code": data.get("postal_code"),
            "region": data.get("region"),
            "county": data.get("county"),
            "parish": data.get("parish"),
            "cae": data.get("cae"),
            "activity_description": data.get("activity"),
            "status": data.get("status"),
            "sector": get_sector(data.get("name", "")),
        })
    
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def get_search_dataframe() -> pd.DataFrame:
    """Get search results as DataFrame (from DB or JSON)"""
    if DB_AVAILABLE:
        try:
            from db import get_connection
            with get_connection() as conn:
                df = pd.read_sql("""
                    SELECT nif, name, source_url as url, city, postal_code, sector
                    FROM companies 
                    WHERE source = 'nif_search'
                    ORDER BY fetched_at DESC
                """, conn)
                
                # Add location column (derived from postal_code and city)
                if not df.empty:
                    df['location'] = df.apply(
                        lambda row: f"{row['postal_code']} {row['city']}".strip() if row['postal_code'] or row['city'] else 'N/A',
                        axis=1
                    )
                
                return df
        except Exception as e:
            print(f"DB error, falling back to JSON: {e}")
    
    # Fallback to JSON
    search_data = load_json_search()
    if not search_data:
        return pd.DataFrame()
    
    rows = []
    for c in search_data:
        location = c.get("location", "N/A")
        city = ""
        postal_code = ""
        
        if location and location != "N/A":
            parts = location.split(maxsplit=1)
            postal_code = parts[0] if parts else ""
            city = parts[1] if len(parts) > 1 else ""
        
        rows.append({
            "nif": c.get("nif"),
            "name": c.get("name", "Unknown"),
            "location": location,
            "url": c.get("url", ""),
            "city": city,
            "postal_code": postal_code,
            "sector": get_sector(c.get("name", "")),
        })
    
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600)
def get_einforma_dataframe(use_historical: bool = True, year: Optional[int] = None) -> pd.DataFrame:
    """Get eInforma companies as DataFrame (from DB or JSON)"""
    if DB_AVAILABLE:
        try:
            from db import get_connection
            with get_connection() as conn:
                sql = """
                    SELECT nif, name, source_url, registration_date, sector
                    FROM companies 
                    WHERE source = 'einforma'
                """
                params = []
                
                if year:
                    sql += " AND EXTRACT(YEAR FROM registration_date) = %s"
                    params.append(year)
                
                sql += " ORDER BY registration_date DESC NULLS LAST"
                
                df = pd.read_sql(sql, conn, params=params)
                return df
        except Exception as e:
            print(f"DB error, falling back to JSON: {e}")
    
    # Fallback to JSON
    einforma_data = load_json_einforma()
    if not einforma_data:
        return pd.DataFrame()
    
    rows = []
    for nif, c in einforma_data.items():
        date_str = c.get("date", "")
        registration_date = None
        if date_str:
            try:
                registration_date = datetime.strptime(date_str, "%d-%m-%Y").date()
            except:
                pass
        
        rows.append({
            "nif": nif,
            "name": c.get("name", "Unknown"),
            "source_url": c.get("url", ""),
            "registration_date": registration_date,
            "date": date_str,
            "sector": get_sector(c.get("name", "")),
        })
    
    df = pd.DataFrame(rows)
    
    if year and not df.empty:
        df = df[df["registration_date"].apply(lambda x: x.year if x else 0) == year]
    
    return df


def load_enriched_data() -> Dict:
    """
    Load enriched data as dict (from DB or JSON)
    Returns dict keyed by NIF with enriched data
    """
    if DB_AVAILABLE:
        try:
            with get_connection() as conn:
                import pandas as pd
                df = pd.read_sql("""
                    SELECT nif, name, phone, email, website, address, 
                           city, postal_code, region, county, parish,
                           cae, activity_description as activity, status
                    FROM companies 
                    WHERE source = 'nif_api'
                """, conn)
                
                # Convert to dict format
                result = {}
                for _, row in df.iterrows():
                    result[row['nif']] = {
                        "name": row['name'],
                        "phone": row['phone'],
                        "email": row['email'],
                        "website": row['website'],
                        "address": row['address'],
                        "city": row['city'],
                        "postal_code": row['postal_code'],
                        "region": row['region'],
                        "county": row['county'],
                        "parish": row['parish'],
                        "cae": row['cae'],
                        "activity": row['activity'],
                        "status": row['status'],
                    }
                return result
        except Exception as e:
            print(f"DB error, falling back to JSON: {e}")
    
    # Fallback to JSON
    return load_json_enriched()


@st.cache_data(ttl=3600)
def get_stats() -> Dict[str, int]:
    """Get dashboard statistics (from DB or JSON)"""
    stats = {
        "einforma_total": 0,
        "enriched_total": 0,
        "enriched_with_contact": 0,
        "search_total": 0,
        "last_update": None,
    }
    
    if DB_AVAILABLE:
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    # eInforma
                    cur.execute("SELECT COUNT(*) FROM companies WHERE source = 'einforma'")
                    result = cur.fetchone()
                    stats["einforma_total"] = result[0] if result else 0
                    
                    # Enriched
                    cur.execute("SELECT COUNT(*) FROM companies WHERE source = 'nif_api'")
                    result = cur.fetchone()
                    stats["enriched_total"] = result[0] if result else 0
                    
                    # With contact
                    cur.execute("""
                        SELECT COUNT(*) FROM companies 
                        WHERE source = 'nif_api' 
                        AND (phone IS NOT NULL OR email IS NOT NULL OR website IS NOT NULL)
                    """)
                    result = cur.fetchone()
                    stats["enriched_with_contact"] = result[0] if result else 0
                    
                    # Search
                    cur.execute("SELECT COUNT(*) FROM companies WHERE source = 'nif_search'")
                    result = cur.fetchone()
                    stats["search_total"] = result[0] if result else 0
                    
                    return stats
        except Exception as e:
            print(f"DB error, falling back to JSON: {e}")
    
    # Fallback to JSON
    einforma = load_json_einforma()
    stats["einforma_total"] = len(einforma)
    
    enriched = load_json_enriched()
    stats["enriched_total"] = len(enriched)
    stats["enriched_with_contact"] = sum(
        1 for c in enriched.values()
        if c.get("phone") or c.get("email") or c.get("website")
    )
    
    search = load_json_search()
    stats["search_total"] = len(search)
    
    if einforma:
        dates = [c.get("date") for c in einforma.values() if c.get("date")]
        if dates:
            stats["last_update"] = dates[0]
    
    return stats


def is_db_available() -> bool:
    """Check if database is available"""
    return DB_AVAILABLE


# For testing
if __name__ == "__main__":
    print(f"Database available: {DB_AVAILABLE}")
    print(f"Stats: {get_stats()}")
    print(f"Enriched: {len(get_enriched_dataframe())} companies")
    print(f"Search: {len(get_search_dataframe())} companies")
    print(f"eInforma: {len(get_einforma_dataframe())} companies")
