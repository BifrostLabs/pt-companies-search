# PT Companies Search — Shell Aliases
# Usage: source aliases.sh

export PT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$HOME/.local/bin:$PATH"

# ── Dashboard ─────────────────────────────────────────────────────────────────
alias pt-dashboard='uvicorn pt_companies_search.dashboard.app:app --host 0.0.0.0 --port 8501 --reload'

# ── Data pipeline ─────────────────────────────────────────────────────────────
alias pt-scrape='pt-search scrape --pages 10'
alias pt-nif-enrich='pt-search enrich --limit 100'
alias pt-nif-search-tech='pt-search search "TECNOLOGIA" --pages 5'

# Full pipeline: scrape -> enrich
alias pt-automate='pt-search scrape --pages 10 && pt-search enrich --limit 100'

# ── Database ──────────────────────────────────────────────────────────────────
alias pt-db-up='docker run -d --name pt-companies-db \
  -e POSTGRES_USER=${DB_USER:-pt_user} \
  -e POSTGRES_PASSWORD=${DB_PASSWORD:-} \
  -e POSTGRES_DB=${DB_NAME:-pt_companies} \
  -p 5432:5432 \
  --platform linux/arm64 \
  postgres:16-alpine'

alias pt-db-down='docker stop pt-companies-db && docker rm pt-companies-db'
alias pt-db-logs='docker logs -f pt-companies-db'
alias pt-db-psql='docker exec -it pt-companies-db psql -U ${DB_USER:-pt_user} -d ${DB_NAME:-pt_companies}'
alias pt-db-init='docker exec -i pt-companies-db psql -U ${DB_USER:-pt_user} -d ${DB_NAME:-pt_companies} < "$PT_DIR/db/init-db.sql"'

echo "[pt] Aliases loaded. Commands: pt-dashboard, pt-scrape, pt-nif-enrich, pt-automate"
