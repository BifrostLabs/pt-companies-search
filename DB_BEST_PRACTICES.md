# Database Best Practices - PT Companies Project

## 🎯 TL;DR: Always Use Transaction-Safe Patterns

**✅ GOOD - Use these:**
```python
from db import get_cursor, transaction

# Option 1: get_cursor() - Recommended for most cases
with get_cursor() as cur:
    cur.execute("INSERT INTO companies ...")
    # ✅ Auto-commits on success, auto-rolls back on error

# Option 2: transaction() - When you need the connection
with transaction() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO companies ...")
    # ✅ Auto-commits on success, auto-rolls back on error

# Option 3: High-level functions - Best for simple operations
from db import upsert_company, bulk_upsert_companies
upsert_company({"nif": "123456789", "name": "ACME LDA"})
```

**❌ BAD - Avoid these:**
```python
from db import get_connection

# ❌ NO auto-commit! Data will be lost!
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO companies ...")
    # ❌ No commit! Transaction lost!

# ❌ Manual commit is error-prone
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO companies ...")
    conn.commit()  # ❌ What if exception happens before this?
```

---

## 📚 Context Managers Guide

### `get_cursor()` - RECOMMENDED ✅

**Best for:** Most queries (reads + writes)

```python
from db import get_cursor

with get_cursor() as cur:
    cur.execute("SELECT * FROM companies")
    results = cur.fetchall()
    # ✅ Auto-commits

with get_cursor(dict_cursor=False) as cur:
    cur.execute("INSERT INTO companies ...")
    # ✅ Auto-commits
```

**Features:**
- ✅ Automatic commit on success
- ✅ Automatic rollback on error
- ✅ Returns RealDictCursor by default
- ✅ Connection pool cleanup

---

### `transaction()` - When You Need Connection ✅

**Best for:** Multiple operations in one transaction, manual cursor control

```python
from db import transaction

with transaction() as conn:
    with conn.cursor() as cur1:
        cur1.execute("INSERT INTO companies ...")
    
    with conn.cursor() as cur2:
        cur2.execute("INSERT INTO enrichment_log ...")
    
    # ✅ Both operations commit together (ACID)
```

**Features:**
- ✅ Automatic commit on success
- ✅ Automatic rollback on error
- ✅ Full connection control
- ✅ ACID semantics for multiple operations

---

### `get_connection()` - Use With Caution ⚠️

**Best for:** Read-only queries, special cases

```python
from db import get_connection

# ⚠️ Only for reads!
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM companies")
        results = cur.fetchall()
    # No commit needed for reads
```

**⚠️ WARNING:**
- ❌ Does NOT auto-commit
- ❌ Does NOT auto-rollback
- ⚠️ Only use for reads or manual transaction control
- ⚠️ If you use this for writes, you MUST call `conn.commit()` manually

---

## 🔍 Real Examples from the Project

### ✅ FIXED: nif_search.py

**Before (broken):**
```python
with get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO companies ...")
    # ❌ No commit! Data lost!
```

**After (fixed):**
```python
with transaction() as conn:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO companies ...")
    # ✅ Auto-commits!
```

### ✅ FIXED: nif_enrich.py

**Before (broken):**
```python
def save_enriched_to_db(companies: dict):
    from db import get_connection
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            for nif, data in companies.items():
                cur.execute("INSERT INTO companies ...")
        # ❌ No commit! All data lost!
```

**After (fixed):**
```python
def save_enriched_to_db(companies: dict):
    from db import transaction
    
    with transaction() as conn:
        with conn.cursor() as cur:
            for nif, data in companies.items():
                cur.execute("INSERT INTO companies ...")
        # ✅ Auto-commits all inserts!
```

### ✅ GOOD: sync_search_to_db.py

```python
with get_cursor() as cur:
    for nif, company in all_companies.items():
        cur.execute("INSERT INTO companies ...")
    # ✅ Auto-commits!
```

---

## 🛠️ High-Level Functions

Prefer these when possible - they handle transactions internally:

```python
from db import (
    upsert_company,           # Single company upsert
    bulk_upsert_companies,    # Bulk upsert
    get_company_by_nif,       # Fetch by NIF
    search_companies,         # Search with filters
    get_sector_stats,         # Aggregations
)

# ✅ Simple and safe
upsert_company({
    "nif": "509442013",
    "name": "ACME TECH LDA",
    "source": "einforma",
    "phone": "+351 21 123 4567",
})

# ✅ Bulk operations
bulk_upsert_companies([
    {"nif": "111111111", "name": "Company A"},
    {"nif": "222222222", "name": "Company B"},
])
```

---

## 🚨 Common Bugs and How to Fix Them

### Bug: Missing Commit

**Symptom:** Data disappears after script runs, no errors shown

**Cause:**
```python
with get_connection() as conn:
    cur.execute("INSERT ...")
    # ❌ No commit!
```

**Fix:**
```python
with transaction() as conn:
    cur.execute("INSERT ...")
    # ✅ Auto-commits
```

### Bug: Partial Commits

**Symptom:** Some data saved, some lost (intermittent)

**Cause:**
```python
for item in items:
    with get_cursor() as cur:
        cur.execute("INSERT ...")
    # ⚠️ Each iteration commits separately
    # If loop fails halfway, partial data committed
```

**Fix (if you want all-or-nothing):**
```python
with transaction() as conn:
    with conn.cursor() as cur:
        for item in items:
            cur.execute("INSERT ...")
    # ✅ All commits together, or all rolls back
```

### Bug: Silent Failures

**Symptom:** Script reports success but no data in DB

**Cause:**
```python
try:
    with get_connection() as conn:
        cur.execute("INSERT ...")
except Exception as e:
    pass  # ❌ Swallowed error, no commit
```

**Fix:**
```python
with transaction() as conn:
    cur.execute("INSERT ...")
    # ✅ Auto-commits, or auto-rolls back with exception
```

---

## 📋 Checklist for New DB Code

Before committing new code that touches the database:

- [ ] Are you using `get_cursor()` or `transaction()`?
- [ ] If using `get_connection()`, is it read-only?
- [ ] Are you handling exceptions properly?
- [ ] Did you test with actual data?
- [ ] Does the data persist after the script exits?
- [ ] Did you check the DB with `pt-db-psql` to verify?

---

## 🔬 Testing Your Code

```bash
# 1. Run your script
python3 your_script.py

# 2. Connect to DB and verify
docker exec -it pt-postgres psql -U pt_user -d pt_companies

# 3. Check if data exists
SELECT COUNT(*) FROM companies WHERE source = 'your_source';

# 4. If count is 0, you have a commit bug!
```

---

## 📖 Further Reading

- PostgreSQL Transactions: https://www.postgresql.org/docs/current/tutorial-transactions.html
- Python DB-API: https://peps.python.org/pep-0249/
- psycopg2 Usage: https://www.psycopg.org/docs/usage.html

---

**Remember: When in doubt, use `get_cursor()` or `transaction()`. Never use `get_connection()` for writes unless you know exactly what you're doing!**
