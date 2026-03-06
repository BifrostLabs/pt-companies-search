# Portugal New Companies - Shell Aliases
# Add to your ~/.bashrc or source directly: source /root/.openclaw/workspace/pt-new-companies/aliases.sh

export PT_COMPANIES_DIR="/root/.openclaw/workspace/pt-new-companies"
export PATH="$HOME/.local/bin:$PATH"

# Database configuration
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-pt_companies}"
export DB_USER="${DB_USER:-pt_user}"
export DB_PASSWORD="${DB_PASSWORD:-pt_secure_pass_2024}"

# Quick commands
alias pt-scrape='cd $PT_COMPANIES_DIR && uv run python scraper.py'
alias pt-dashboard='cd $PT_COMPANIES_DIR && uv run streamlit run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true'
alias pt-enrich='cd $PT_COMPANIES_DIR && uv run python enrich.py'
alias pt-nif-enrich='cd $PT_COMPANIES_DIR && uv run python nif_enrich.py'
alias pt-nif-search='cd $PT_COMPANIES_DIR && uv run python nif_search.py'
alias pt-enrich-search='cd $PT_COMPANIES_DIR && uv run python enrich_search_results.py'
alias pt-schedule='cd $PT_COMPANIES_DIR && uv run python schedule.py'
alias pt-automate='cd $PT_COMPANIES_DIR && uv run python automate.py'

# Database commands
alias pt-db-up='cd $PT_COMPANIES_DIR && docker-compose -f docker-compose.postgres.yml up -d'
alias pt-db-down='cd $PT_COMPANIES_DIR && docker-compose -f docker-compose.postgres.yml down'
alias pt-db-logs='cd $PT_COMPANIES_DIR && docker-compose -f docker-compose.postgres.yml logs -f'
alias pt-db-psql='cd $PT_COMPANIES_DIR && docker-compose -f docker-compose.postgres.yml exec postgres psql -U pt_user -d pt_companies'
alias pt-db-migrate='cd $PT_COMPANIES_DIR && uv run python migrate_to_db.py'
alias pt-db-test='cd $PT_COMPANIES_DIR && uv run python db.py'
alias pt-db-sync='cd $PT_COMPANIES_DIR && uv run python db_enrich_sync.py'
alias pt-db-sync-search='cd $PT_COMPANIES_DIR && uv run python sync_search_to_db.py'

# View latest data
alias pt-latest='cat $PT_COMPANIES_DIR/data/companies_*.json | jq -r ".companies[:10] | .[] | \"\(.nif) | \(.date) | \(.name)\"" 2>/dev/null || echo "Run pt-scrape first"'

# Count companies
alias pt-count='cat $PT_COMPANIES_DIR/data/companies_*.json | jq ".count" 2>/dev/null || echo "No data"'

# Quick search
pt-search() {
    cd $PT_COMPANIES_DIR
    uv run python -c "
import json, glob, sys
files = sorted(glob.glob('data/companies_*.json'), reverse=True)
if not files:
    print('No data. Run pt-scrape first.')
    sys.exit(1)
with open(files[0]) as f:
    data = json.load(f)
search = ' '.join(sys.argv[1:]).lower()
for c in data['companies']:
    if search in c['name'].lower():
        print(f\"{c['nif']} | {c['date']} | {c['name']}\")
" "$@"
}

echo "✅ Portugal New Companies aliases loaded"
echo ""
echo "   🚀 Full Automation:"
echo "   pt-automate             - Run all: scrape + search + enrich + sync"
echo "                           Options: --skip-scrape, --skip-search, --enrich-limit N"
echo ""
echo "   Scraping & Enrichment:"
echo "   pt-scrape         - Fetch latest companies from eInforma.pt"
echo "   pt-nif-search     - Search NIF.pt database directly"
echo "   pt-enrich-search  - Enrich search results with contact details"
echo "   pt-enrich         - Enrich with additional data"
echo "   pt-nif-enrich     - Enrich with NIF.pt API (address, phone, email)"
echo "                    Use --status to check rate limits"
echo "   pt-schedule       - Run daily scheduler"
echo ""
echo "   Dashboard:"
echo "   pt-dashboard      - Launch Streamlit dashboard"
echo ""
echo "   Database (PostgreSQL):"
echo "   pt-db-up          - Start PostgreSQL container"
echo "   pt-db-down        - Stop PostgreSQL container"
echo "   pt-db-logs        - View PostgreSQL logs"
echo "   pt-db-psql        - Open psql shell"
echo "   pt-db-migrate     - Migrate JSON data to PostgreSQL"
echo "   pt-db-test        - Test database connection"
echo "   pt-db-sync        - Sync enriched data between JSON and DB"
echo ""
echo "   Quick Commands:"
echo "   pt-latest         - Show latest 10 companies"
echo "   pt-count          - Count total companies"
echo "   pt-search <term>  - Search by name"
