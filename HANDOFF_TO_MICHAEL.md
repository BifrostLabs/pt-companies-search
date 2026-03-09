# 🤝 Handoff to Michael - Backend Standardization Complete

**From:** Dwight (Backend Engineer)  
**To:** Michael (Enricher Rebuild)  
**Date:** March 9, 2026  
**Status:** ✅ Ready for your enricher rebuild

---

## 📋 What I Did

I've standardized the database layer to fix the missing commit bugs. Here's what changed:

### 🔧 Core Changes

1. **New `transaction()` context manager** - Use this for all writes!
   ```python
   from db import transaction
   
   with transaction() as conn:
       with conn.cursor() as cur:
           cur.execute("INSERT INTO companies ...")
       # ✅ Auto-commits here!
   ```

2. **Enhanced `get_cursor()`** - Still the recommended way for most queries
   ```python
   from db import get_cursor
   
   with get_cursor() as cur:
       cur.execute("INSERT INTO companies ...")
   # ✅ Auto-commits!
   ```

3. **Fixed `nif_search.py` and `nif_enrich.py`** - Both now properly commit data

---

## 🎯 What You Need to Know for the Enricher Rebuild

### ✅ Use These Patterns:

```python
# Pattern 1: get_cursor() - Recommended for most cases
from db import get_cursor

def save_enriched_company(nif: str, data: dict):
    with get_cursor() as cur:
        cur.execute("""
            INSERT INTO companies (nif, name, phone, email, ...)
            VALUES (%s, %s, %s, %s, ...)
            ON CONFLICT (nif) DO UPDATE SET ...
        """, (nif, data['name'], data['phone'], data['email']))
    # ✅ Auto-commits!

# Pattern 2: transaction() - For batch operations
from db import transaction

def save_enriched_batch(companies: list):
    with transaction() as conn:
        with conn.cursor() as cur:
            for company in companies:
                cur.execute("INSERT INTO companies ...")
        # ✅ All commits together (ACID)

# Pattern 3: High-level functions - Simplest approach
from db import upsert_company, bulk_upsert_companies

def save_enriched_simple(company_data: dict):
    upsert_company(company_data)
    # ✅ Handles everything internally
```

### ❌ Avoid These Patterns:

```python
# ❌ BAD: Using get_connection() for writes
from db import get_connection

with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT ...")
    # ❌ No commit! Data lost!

# ❌ BAD: Manual commits
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT ...")
    conn.commit()  # ❌ Error-prone, what if exception?
```

---

## 📚 Resources for You

1. **`DB_BEST_PRACTICES.md`** - Read this first!
   - Recommended patterns
   - Common bugs and fixes
   - Real examples from the codebase
   - Testing guidelines

2. **`CHANGELOG_DB_STANDARDIZATION.md`** - Technical details
   - What changed and why
   - Migration guide
   - Testing procedures

3. **`db.py`** - The source of truth
   - Look at the docstrings
   - See the new `transaction()` implementation

---

## 🚀 Quick Start for Your Enricher

```python
#!/usr/bin/env python3
"""
New enricher - Best practices example
"""

from db import transaction, get_cursor, upsert_company
from typing import Dict, List

def enrich_and_save(nif: str, api_data: dict) -> bool:
    """
    Enrich a company and save to DB
    
    ✅ This uses transaction() for ACID semantics
    """
    try:
        with transaction() as conn:
            with conn.cursor() as cur:
                # Enrich
                enriched = {
                    "nif": nif,
                    "name": api_data.get("name"),
                    "phone": api_data.get("phone"),
                    "email": api_data.get("email"),
                    "website": api_data.get("website"),
                    "address": api_data.get("address"),
                    "source": "nif_api",
                }
                
                # Save
                cur.execute("""
                    INSERT INTO companies (
                        nif, name, source, phone, email, website, address, enriched_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (nif) DO UPDATE SET
                        phone = EXCLUDED.phone,
                        email = EXCLUDED.email,
                        website = EXCLUDED.website,
                        address = COALESCE(EXCLUDED.address, companies.address),
                        enriched_at = NOW()
                """, (
                    enriched['nif'],
                    enriched['name'],
                    enriched['source'],
                    enriched['phone'],
                    enriched['email'],
                    enriched['website'],
                    enriched['address']
                ))
                
                # ✅ Auto-commits here!
                return True
                
    except Exception as e:
        print(f"Error enriching {nif}: {e}")
        # ✅ Auto-rollback on exception
        return False


def batch_enrich_and_save(companies: List[Dict]) -> int:
    """
    Enrich multiple companies in one transaction
    
    ✅ All-or-nothing: either all succeed or all rollback
    """
    count = 0
    
    with transaction() as conn:
        with conn.cursor() as cur:
            for company in companies:
                cur.execute("""
                    INSERT INTO companies (...)
                    VALUES (...)
                    ON CONFLICT (nif) DO UPDATE SET ...
                """, (...))
                count += 1
            
            # ✅ All commits together
    
    return count


def simple_enrich_and_save(nif: str, api_data: dict) -> bool:
    """
    Simplest approach - use high-level function
    
    ✅ Let the framework handle transactions
    """
    enriched = {
        "nif": nif,
        "name": api_data.get("name"),
        "phone": api_data.get("phone"),
        "email": api_data.get("email"),
        "source": "nif_api",
    }
    
    return upsert_company(enriched)


# Example usage
if __name__ == "__main__":
    # Single enrichment
    api_response = {"name": "ACME LDA", "phone": "+351 21 123 4567"}
    success = enrich_and_save("123456789", api_response)
    
    # Batch enrichment
    companies = [
        {"nif": "111111111", "name": "Company A"},
        {"nif": "222222222", "name": "Company B"},
    ]
    count = batch_enrich_and_save(companies)
    print(f"Enriched {count} companies")
```

---

## 🧪 Testing Your Enricher

```bash
# 1. Start PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# 2. Run your enricher
python3 your_enricher.py --limit 10

# 3. Verify data persists
docker exec -it pt-postgres psql -U pt_user -d pt_companies

# In psql:
SELECT COUNT(*) FROM companies WHERE enriched_at IS NOT NULL;
SELECT * FROM companies WHERE enriched_at IS NOT NULL LIMIT 5;

# 4. If count is 0, you have a commit bug!
# 5. Check DB_BEST_PRACTICES.md for debugging
```

---

## 🎓 Key Principles

1. **Default to `get_cursor()`** - It handles 90% of cases
2. **Use `transaction()` for batches** - ACID semantics for multiple operations
3. **Avoid `get_connection()`** - Unless you really need manual control
4. **Test data persistence** - Don't assume it worked
5. **Read the docs** - DB_BEST_PRACTICES.md has everything

---

## 🚨 Watch Out For

1. **Silent failures** - Always check if data actually persisted
2. **Partial commits** - Use `transaction()` for all-or-nothing batches
3. **Exception handling** - Don't swallow exceptions without logging
4. **Rate limiting** - Already handled in nif_enrich.py, reuse that logic

---

## 📞 Questions?

If you hit any issues:
1. Check `DB_BEST_PRACTICES.md` first
2. Look at `nif_search.py` and `nif_enrich.py` for examples
3. The `db.py` docstrings are your friend
4. Test in Docker to verify data persistence

---

## ✅ Checklist for Your Enricher

Before you submit your code:

- [ ] Using `get_cursor()` or `transaction()` for all writes
- [ ] No manual `conn.commit()` calls
- [ ] Exception handling in place
- [ ] Tested with real data in Docker
- [ ] Verified data persists in PostgreSQL
- [ ] Read `DB_BEST_PRACTICES.md`

---

**The backend is now solid. Your enricher will have a reliable foundation. Good luck! 🚀**

— Dwight
