from pt_companies_search.core.database import search_companies, test_connection
from pt_companies_search.core.config import config

print("Testing search_companies...")
print(f"DB Config: {config.DB_CONFIG}")

if not test_connection():
    print("❌ Database connection failed")
    exit(1)

# Test 1: Get unenriched companies
companies = search_companies(is_enriched=False, limit=5)
print(f"\n✅ Found {len(companies)} unenriched companies")
if companies:
    print(f"First company: {companies[0]['nif']} - {companies[0]['name']} (source: {companies[0]['source']})")

# Test 2: Get all nif_search companies
nif_search = search_companies(source='nif_search', limit=5)
print(f"\n✅ Found {len(nif_search)} nif_search companies")
if nif_search:
    print(f"First company: {nif_search[0]['nif']} - {nif_search[0]['name']}")

# Test 3: Get unenriched nif_search companies
unenriched_nif = search_companies(source='nif_search', is_enriched=False, limit=5)
print(f"\n✅ Found {len(unenriched_nif)} unenriched nif_search companies")
if unenriched_nif:
    print(f"First company: {unenriched_nif[0]['nif']} - {unenriched_nif[0]['name']}")
