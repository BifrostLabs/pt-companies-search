# NIF Search Routing Logic - Implementation Summary

## Overview
Implemented conditional routing for NIF search results based on contact availability.

## Database Changes

### New Table: `leads_without_personal_data`
- Stores companies WITHOUT contact info (no phone, email, or website)
- Same schema as `companies` table
- Separate from main database to keep leads clean

### Routing Logic
```python
def has_contact_info(company: Dict[str, Any]) -> bool:
    """Check if company has any contact information"""
    return bool(
        company.get("phone") or 
        company.get("email") or 
        company.get("website")
    )

def route_company_by_contact(company: Dict[str, Any]) -> str:
    """
    Route company to appropriate table based on contact availability.
    Returns: "companies" | "leads_without_personal_data" | "error"
    """
```

## Flow

### 1. Search Phase
- NIF search finds companies → saves basic data to `companies` table
- Source: `nif_search`
- No contact info at this stage (just NIF, name, city)

### 2. Enrichment Phase
- Enricher fetches full data from NIF.pt API
- Gets contact info (phone, email, website)
- **Routing Decision:**
  - ✅ **HAS contact** → Save to `companies` table (shows in dashboard)
  - ❌ **NO contact** → Save to `leads_without_personal_data` table (hidden from dashboard)

### 3. Dashboard Display
- https://dash.bifrostlabs.xyz/nif shows only companies with contact info
- Clean data, ready for outreach

## Testing

### Manual Test
```bash
# Run enrichment with routing
kubectl run enrich-test-$(date +%s) --namespace=pt-companies \
  --image=ghcr.io/bifrostlabs/pt-companies-enricher:latest \
  --restart=Never --rm -i --tty \
  --env="DB_HOST=pt-companies-postgresql" \
  --env="DB_NAME=pt_companies" \
  --env="DB_PORT=5432" \
  --env="DB_USER=pt_user" \
  --env="DB_PASSWORD=v857ZExfpsOEF7sUNEnXMtHW" \
  --env="NIF_API_KEY=b44ebcd27f1b24fe2abc58e392d496e2" \
  -- python -m pt_companies_search.cli enrich --all-sectors --source nif_search --limit 5
```

### Check Results
```bash
# Check routing results
export KUBECONFIG=/root/.kube/config-k3s-tailscale
DB_USER=$(kubectl get secret pt-companies-postgresql -n pt-companies -o jsonpath='{.data.username}' | base64 -d)

# Main companies (with contact)
kubectl exec pt-companies-postgresql-0 -n pt-companies -- psql -U "$DB_USER" -d pt_companies -c "
SELECT COUNT(*) as companies_with_contact 
FROM companies 
WHERE source = 'nif_api' AND enriched_at IS NOT NULL;
"

# Leads without contact
kubectl exec pt-companies-postgresql-0 -n pt-companies -- psql -U "$DB_USER" -d pt_companies -c "
SELECT COUNT(*) as leads_without_contact 
FROM leads_without_personal_data;
"
```

## Benefits

1. **Clean Dashboard**: Only shows actionable leads with contact info
2. **Data Separation**: Keeps non-contactable companies separate
3. **Easy to Query**: Can still access leads without contact for future enrichment
4. **Smart Routing**: Automatic routing based on data availability

## Files Modified

1. **Database Module** (`pt_companies_search/core/database.py`)
   - Added `has_contact_info()` function
   - Added `upsert_lead_without_contact()` function
   - Added `route_company_by_contact()` function

2. **CLI** (`pt_companies_search/cli.py`)
   - Updated enrich function to use routing
   - Shows which table data was saved to

3. **Database Schema**
   - Created `leads_without_personal_data` table
   - Added indexes for performance

## Next Steps

1. Run enrichment on existing NIF search data
2. Verify routing is working correctly
3. Update dashboard to show counts of leads with/without contact
4. Consider adding a separate dashboard view for leads without contact
