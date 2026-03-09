#!/usr/bin/env python3
"""
Database module for PT Companies
PostgreSQL connection and operations
"""

import os
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2.pool import SimpleConnectionPool

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "pt_companies"),
    "user": os.getenv("DB_USER", "pt_user"),
    "password": os.getenv("DB_PASSWORD", "pt_secure_pass_2024"),
}

# Connection pool
_pool: Optional[SimpleConnectionPool] = None


def get_pool() -> SimpleConnectionPool:
    """Get or create connection pool"""
    global _pool
    if _pool is None:
        _pool = SimpleConnectionPool(1, 10, **DB_CONFIG)
    return _pool


@contextmanager
def get_connection():
    """
    Get a connection from the pool (NO transaction handling).
    
    ⚠️  WARNING: This does NOT automatically commit/rollback!
    For writes, use get_cursor() or transaction() instead.
    Only use this for:
    - Read-only queries
    - Manual transaction control
    - When you need the raw connection
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


@contextmanager
def transaction():
    """
    Get a connection with AUTOMATIC transaction handling.
    
    ✅ Commits on success
    ❌ Rolls back on exception
    
    Example:
        with transaction() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO companies ...")
                # Auto-commits here
    """
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()  # ✅ Auto-commit on success
    except Exception:
        conn.rollback()  # ❌ Auto-rollback on error
        raise
    finally:
        pool.putconn(conn)


@contextmanager
def get_cursor(dict_cursor=True):
    """
    Get a cursor with automatic transaction handling.
    
    ✅ Commits on success
    ❌ Rolls back on exception
    
    This is the RECOMMENDED way for most queries.
    """
    with transaction() as conn:
        cursor_factory = RealDictCursor if dict_cursor else None
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            yield cur
            # transaction() handles commit/rollback


def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False


# ==================== COMPANY OPERATIONS ====================

def upsert_company(company: Dict[str, Any]) -> bool:
    """Insert or update a company record"""
    # Ensure all required fields have defaults
    safe_company = {
        "nif": company.get("nif"),
        "name": company.get("name"),
        "source": company.get("source"),
        "source_url": company.get("source_url"),
        "registration_date": company.get("registration_date"),
        "status": company.get("status"),
        "phone": company.get("phone"),
        "email": company.get("email"),
        "website": company.get("website"),
        "fax": company.get("fax"),
        "address": company.get("address"),
        "city": company.get("city"),
        "postal_code": company.get("postal_code"),
        "region": company.get("region"),
        "county": company.get("county"),
        "parish": company.get("parish"),
        "cae": company.get("cae"),
        "activity_description": company.get("activity_description"),
        "sector": company.get("sector"),
        "company_nature": company.get("company_nature"),
        "capital": company.get("capital"),
        "enriched_at": company.get("enriched_at"),
    }
    
    # If this is enriched data (has contact info), force update those fields
    is_enriched = company.get("source") == "nif_api"
    
    if is_enriched:
        sql = """
        INSERT INTO companies (
            nif, name, source, source_url, registration_date, status,
            phone, email, website, fax, address, city, postal_code,
            region, county, parish, cae, activity_description, sector,
            company_nature, capital, enriched_at
        ) VALUES (
            %(nif)s, %(name)s, %(source)s, %(source_url)s, %(registration_date)s, %(status)s,
            %(phone)s, %(email)s, %(website)s, %(fax)s, %(address)s, %(city)s, %(postal_code)s,
            %(region)s, %(county)s, %(parish)s, %(cae)s, %(activity_description)s, %(sector)s,
            %(company_nature)s, %(capital)s, %(enriched_at)s
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
            sector = COALESCE(EXCLUDED.sector, companies.sector),
            status = COALESCE(EXCLUDED.status, companies.status),
            enriched_at = EXCLUDED.enriched_at,
            last_verified_at = NOW()
        """
    else:
        sql = """
        INSERT INTO companies (
            nif, name, source, source_url, registration_date, status,
            phone, email, website, fax, address, city, postal_code,
            region, county, parish, cae, activity_description, sector,
            company_nature, capital, enriched_at
        ) VALUES (
            %(nif)s, %(name)s, %(source)s, %(source_url)s, %(registration_date)s, %(status)s,
            %(phone)s, %(email)s, %(website)s, %(fax)s, %(address)s, %(city)s, %(postal_code)s,
            %(region)s, %(county)s, %(parish)s, %(cae)s, %(activity_description)s, %(sector)s,
            %(company_nature)s, %(capital)s, %(enriched_at)s
        )
        ON CONFLICT (nif) DO UPDATE SET
            name = EXCLUDED.name,
            phone = COALESCE(EXCLUDED.phone, companies.phone),
            email = COALESCE(EXCLUDED.email, companies.email),
            website = COALESCE(EXCLUDED.website, companies.website),
            address = COALESCE(EXCLUDED.address, companies.address),
            city = COALESCE(EXCLUDED.city, companies.city),
            postal_code = COALESCE(EXCLUDED.postal_code, companies.postal_code),
            region = COALESCE(EXCLUDED.region, companies.region),
            county = COALESCE(EXCLUDED.county, companies.county),
            parish = COALESCE(EXCLUDED.parish, companies.parish),
            cae = COALESCE(EXCLUDED.cae, companies.cae),
            activity_description = COALESCE(EXCLUDED.activity_description, companies.activity_description),
            sector = COALESCE(EXCLUDED.sector, companies.sector),
            status = COALESCE(EXCLUDED.status, companies.status),
            enriched_at = COALESCE(EXCLUDED.enriched_at, companies.enriched_at),
            last_verified_at = NOW()
        """
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute(sql, safe_company)
        return True
    except Exception as e:
        print(f"Error upserting company {company.get('nif')}: {e}")
        return False


def bulk_upsert_companies(companies: List[Dict[str, Any]]) -> int:
    """Bulk insert/update companies"""
    if not companies:
        return 0
    
    sql = """
    INSERT INTO companies (
        nif, name, source, source_url, registration_date, status,
        phone, email, website, address, city, postal_code,
        region, county, cae, activity_description, sector
    ) VALUES %s
    ON CONFLICT (nif) DO UPDATE SET
        name = EXCLUDED.name,
        phone = COALESCE(EXCLUDED.phone, companies.phone),
        email = COALESCE(EXCLUDED.email, companies.email),
        website = COALESCE(EXCLUDED.website, companies.website),
        city = COALESCE(EXCLUDED.city, companies.city),
        region = COALESCE(EXCLUDED.region, companies.region),
        sector = COALESCE(EXCLUDED.sector, companies.sector)
    """
    
    # Prepare data
    values = [
        (
            c.get("nif"), c.get("name"), c.get("source"), c.get("source_url"),
            c.get("registration_date"), c.get("status"),
            c.get("phone"), c.get("email"), c.get("website"),
            c.get("address"), c.get("city"), c.get("postal_code"),
            c.get("region"), c.get("county"), c.get("cae"),
            c.get("activity_description"), c.get("sector")
        )
        for c in companies
    ]
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            execute_values(cur, sql, values)
        return len(companies)
    except Exception as e:
        print(f"Error bulk upserting companies: {e}")
        return 0


def get_company_by_nif(nif: str) -> Optional[Dict[str, Any]]:
    """Get a company by NIF"""
    sql = "SELECT * FROM companies WHERE nif = %s"
    
    with get_cursor() as cur:
        cur.execute(sql, (nif,))
        result = cur.fetchone()
        return dict(result) if result else None


def search_companies(
    query: Optional[str] = None,
    sector: Optional[str] = None,
    region: Optional[str] = None,
    city: Optional[str] = None,
    source: Optional[str] = None,
    has_phone: bool = False,
    has_email: bool = False,
    has_website: bool = False,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Search companies with filters"""
    conditions = []
    params = []
    
    if query:
        conditions.append("search_vector @@ plainto_tsquery('portuguese', %s)")
        params.append(query)
    
    if sector:
        conditions.append("sector = %s")
        params.append(sector)
    
    if region:
        conditions.append("region = %s")
        params.append(region)
    
    if city:
        conditions.append("city = %s")
        params.append(city)
    
    if source:
        conditions.append("source = %s")
        params.append(source)
    
    if has_phone:
        conditions.append("phone IS NOT NULL")
    
    if has_email:
        conditions.append("email IS NOT NULL")
    
    if has_website:
        conditions.append("website IS NOT NULL")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"""
    SELECT * FROM companies
    WHERE {where_clause}
    ORDER BY 
        CASE WHEN phone IS NOT NULL THEN 0 ELSE 1 END,
        CASE WHEN email IS NOT NULL THEN 0 ELSE 1 END,
        registration_date DESC NULLS LAST
    LIMIT %s OFFSET %s
    """
    
    params.extend([limit, offset])
    
    with get_cursor() as cur:
        cur.execute(sql, params)
        return [dict(row) for row in cur.fetchall()]


def count_companies(
    query: Optional[str] = None,
    sector: Optional[str] = None,
    region: Optional[str] = None,
    source: Optional[str] = None,
) -> int:
    """Count companies matching filters"""
    conditions = []
    params = []
    
    if query:
        conditions.append("search_vector @@ plainto_tsquery('portuguese', %s)")
        params.append(query)
    
    if sector:
        conditions.append("sector = %s")
        params.append(sector)
    
    if region:
        conditions.append("region = %s")
        params.append(region)
    
    if source:
        conditions.append("source = %s")
        params.append(source)
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    sql = f"SELECT COUNT(*) as count FROM companies WHERE {where_clause}"
    
    with get_cursor() as cur:
        cur.execute(sql, params)
        result = cur.fetchone()
        return result["count"] if result else 0


# ==================== AGGREGATION QUERIES ====================

def get_sector_stats() -> List[Dict[str, Any]]:
    """Get statistics by sector"""
    sql = """
    SELECT 
        sector,
        COUNT(*) as total,
        COUNT(phone) as with_phone,
        COUNT(email) as with_email,
        COUNT(website) as with_website
    FROM companies
    GROUP BY sector
    ORDER BY total DESC
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
        return [dict(row) for row in cur.fetchall()]


def get_region_stats() -> List[Dict[str, Any]]:
    """Get statistics by region"""
    sql = """
    SELECT 
        region,
        COUNT(*) as total
    FROM companies
    WHERE region IS NOT NULL
    GROUP BY region
    ORDER BY total DESC
    LIMIT 20
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
        return [dict(row) for row in cur.fetchall()]


def get_city_stats(limit: int = 20) -> List[Dict[str, Any]]:
    """Get statistics by city"""
    sql = """
    SELECT 
        city,
        COUNT(*) as total
    FROM companies
    WHERE city IS NOT NULL AND city != ''
    GROUP BY city
    ORDER BY total DESC
    LIMIT %s
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (limit,))
        return [dict(row) for row in cur.fetchall()]


def get_source_stats() -> List[Dict[str, Any]]:
    """Get statistics by source"""
    sql = """
    SELECT 
        source,
        COUNT(*) as total,
        COUNT(phone) as with_phone,
        COUNT(email) as with_email,
        COUNT(website) as with_website
    FROM companies
    GROUP BY source
    ORDER BY total DESC
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
        return [dict(row) for row in cur.fetchall()]


def get_contact_coverage() -> Dict[str, int]:
    """Get overall contact coverage statistics"""
    sql = """
    SELECT 
        COUNT(*) as total,
        COUNT(phone) as with_phone,
        COUNT(email) as with_email,
        COUNT(website) as with_website,
        COUNT(CASE WHEN phone IS NULL AND email IS NULL AND website IS NULL THEN 1 END) as no_contact
    FROM companies
    """
    
    with get_cursor() as cur:
        cur.execute(sql)
        result = cur.fetchone()
        return dict(result) if result else {}


# ==================== RATE LIMITING ====================

def check_rate_limit(service: str) -> Dict[str, Any]:
    """Check rate limit status for a service"""
    sql = """
    SELECT * FROM rate_limits WHERE service = %s
    """
    
    with get_cursor() as cur:
        cur.execute(sql, (service,))
        result = cur.fetchone()
        return dict(result) if result else {}


def increment_rate_limit(service: str) -> bool:
    """Increment rate limit counter"""
    sql = """
    UPDATE rate_limits
    SET 
        requests_count = requests_count + 1,
        daily_count = daily_count + 1,
        monthly_count = monthly_count + 1
    WHERE service = %s
    """
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute(sql, (service,))
        return True
    except Exception as e:
        print(f"Error incrementing rate limit: {e}")
        return False


def reset_rate_limits(service: str) -> bool:
    """Reset rate limit counters"""
    sql = """
    UPDATE rate_limits
    SET 
        requests_count = 0,
        window_start = NOW(),
        daily_count = 0,
        daily_start = NOW(),
        monthly_count = 0,
        monthly_start = NOW()
    WHERE service = %s
    """
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute(sql, (service,))
        return True
    except Exception as e:
        print(f"Error resetting rate limits: {e}")
        return False


# ==================== ENRICHMENT LOG ====================

def log_enrichment(nif: str, source: str, status: str, error_message: str = None) -> bool:
    """Log an enrichment attempt"""
    sql = """
    INSERT INTO enrichment_log (nif, source, status, error_message)
    VALUES (%s, %s, %s, %s)
    """
    
    try:
        with get_cursor(dict_cursor=False) as cur:
            cur.execute(sql, (nif, source, status, error_message))
        return True
    except Exception as e:
        print(f"Error logging enrichment: {e}")
        return False


if __name__ == "__main__":
    # Test connection
    if test_connection():
        print("✅ Database connection successful")
        
        # Test query
        stats = get_contact_coverage()
        print(f"📊 Database stats: {stats}")
    else:
        print("❌ Database connection failed")
        print("Make sure PostgreSQL is running:")
        print("  cd /root/.openclaw/workspace/pt-new-companies")
        print("  docker-compose -f docker-compose.postgres.yml up -d")
