# Database Standardization Changes - March 9, 2026

**Author:** Dwight (Backend Engineer)  
**Date:** March 9, 2026  
**Issue:** Missing `conn.commit()` calls causing data loss in `nif_search.py` and `nif_enrich.py`

---

## 🎯 Problem Statement

Multiple bugs were discovered where database writes were not being committed:

1. **`nif_search.py`** - Companies scraped from NIF.pt were not being saved to PostgreSQL
2. **`nif_enrich.py`** - Enriched company data was not being saved to PostgreSQL
3. **Root cause:** `get_connection()` context manager doesn't handle transactions automatically

This led to silent data loss - scripts would run successfully but no data would persist.

---

## ✅ Solution: Transaction-Safe Context Managers

### 1. New `transaction()` Context Manager

Added a new context manager in `db.py` that handles commit/rollback automatically:

```python
@contextmanager
def transaction():
    """
    Get a connection with AUTOMATIC transaction handling.
    
    ✅ Commits on success
    ❌ Rolls back on exception
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
```

### 2. Updated `get_cursor()` to Use `transaction()`

Now `get_cursor()` delegates to `transaction()` for consistent behavior:

```python
@contextmanager
def get_cursor(dict_cursor=True):
    """
    Get a cursor with automatic transaction handling.
    
    ✅ Commits on success
    ❌ Rolls back on exception
    """
    with transaction() as conn:
        cursor_factory = RealDictCursor if dict_cursor else None
        with conn.cursor(cursor_factory=cursor_factory) as cur:
            yield cur
            # transaction() handles commit/rollback
```

### 3. Updated `get_connection()` Documentation

Added clear warnings about manual transaction control:

```python
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
```

---

## 🔧 Files Modified

### `db.py`
- ✅ Added `transaction()` context manager
- ✅ Updated `get_cursor()` to use `transaction()`
- ✅ Added documentation warnings to `get_connection()`

### `nif_search.py`
- ✅ Changed `get_connection()` → `transaction()`
- ✅ Removed manual `conn.commit()` call (now automatic)

### `nif_enrich.py`
- ✅ Changed `get_connection()` → `transaction()` in `save_enriched_to_db()`

---

## 📚 New Documentation

### `DB_BEST_PRACTICES.md`
Created comprehensive guide covering:
- ✅ Recommended patterns (`get_cursor()`, `transaction()`)
- ❌ Anti-patterns (manual commits, `get_connection()` for writes)
- 🔍 Real-world examples from the codebase
- 🚨 Common bugs and fixes
- 📋 Checklist for new DB code
- 🔬 Testing guidelines

---

## 🧪 Testing

### Syntax Validation
```bash
✅ All Python files compile successfully
```

### Manual Testing Required
Since psycopg2 is not installed in host environment, Docker testing is required:

```bash
# 1. Start PostgreSQL
docker-compose -f docker-compose.postgres.yml up -d

# 2. Run scraper
python3 nif_search.py "TECNOLOGIA" --pages 2

# 3. Verify data persists
docker exec -it pt-postgres psql -U pt_user -d pt_companies -c "SELECT COUNT(*) FROM companies WHERE source = 'nif_search';"

# 4. Run enricher
python3 nif_enrich.py --source latest --limit 10

# 5. Verify enriched data persists
docker exec -it pt-postgres psql -U pt_user -d pt_companies -c "SELECT COUNT(*) FROM companies WHERE phone IS NOT NULL;"
```

---

## 🎓 Best Practices Going Forward

### ✅ DO:
1. Use `get_cursor()` for most queries (recommended)
2. Use `transaction()` when you need connection-level control
3. Use high-level functions (`upsert_company`, `bulk_upsert_companies`)
4. Read `DB_BEST_PRACTICES.md` before writing new DB code
5. Test data persistence after running scripts

### ❌ DON'T:
1. Use `get_connection()` for writes
2. Swallow exceptions without logging
3. Commit manually inside context managers
4. Assume data is saved without verifying

---

## 🔄 Migration Impact

### Backward Compatibility
✅ All existing code continues to work:
- `get_cursor()` - Behavior unchanged (still auto-commits)
- `get_connection()` - Behavior unchanged (still manual)
- High-level functions - Behavior unchanged

### No Breaking Changes
All changes are additive:
- New `transaction()` context manager
- Enhanced documentation
- Fixed bugs

---

## 🚀 Next Steps

### For Michael (Enricher Rebuild):
1. Review `DB_BEST_PRACTICES.md`
2. Use `transaction()` or `get_cursor()` for all writes
3. Test data persistence after each run
4. Consider using `bulk_upsert_companies()` for batch operations

### For the Team:
1. Review this changelog
2. Test the fixes in Docker environment
3. Update any scripts using `get_connection()` for writes
4. Follow the new best practices guide

---

## 📊 Impact Summary

- **Files changed:** 3 (db.py, nif_search.py, nif_enrich.py)
- **New files:** 2 (DB_BEST_PRACTICES.md, CHANGELOG_DB_STANDARDIZATION.md)
- **Bugs fixed:** 2 critical data loss bugs
- **Breaking changes:** 0
- **New features:** 1 (`transaction()` context manager)

---

**Status:** ✅ Ready for review and testing
