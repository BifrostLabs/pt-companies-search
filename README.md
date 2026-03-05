# 🇵🇹 Portugal New Companies Dashboard

Multi-page Streamlit dashboard for tracking new Portuguese companies.

## 📂 Structure

```
pt-new-companies/
├── app.py                      # Main entry point (Home)
├── pages/
│   ├── 1_📋_eInforma_pt.py    # eInforma.pt data
│   └── 2_📊_NIF_pt.py         # NIF.pt data
├── data/
│   ├── companies_*.json       # eInforma.pt snapshots
│   ├── companies_enriched.json # Enriched data
│   └── nif_search_*.json      # NIF.pt search results
└── scripts/
    ├── scraper.py             # Scrape eInforma.pt
    ├── nif_enrich.py          # Enrich via NIF.pt API
    └── nif_search.py          # Search NIF.pt
```

## 🌐 URLs

- **Home:** http://100.117.228.92:8501
- **eInforma.pt:** http://100.117.228.92:8501/📋_eInforma_pt
- **NIF.pt:** http://100.117.228.92:8501/📊_NIF_pt

## 🚀 Quick Start

```bash
# Load aliases
source /root/.openclaw/workspace/pt-new-companies/aliases.sh

# 🎯 ONE COMMAND TO DO EVERYTHING:
pt-automate              # Scrape + Search + Enrich + Sync to DB

# Or run individual steps:
pt-scrape                # Just scrape eInforma.pt
pt-nif-search "HOTEL"    # Just search NIF.pt
pt-nif-enrich            # Just enrich companies
pt-dashboard             # Launch dashboard
```

## 📊 Pages

### 📋 eInforma.pt
- Companies from eInforma.pt (last 7 days or historical)
- Filters: date, sector, search
- Shows enriched data (phone, email, city)
- Export: CSV

### 📊 NIF.pt

**Tab 1: Enriquecidos (API)**
- Companies enriched with full contact details
- Filter: search, has phone, has email
- Export: CSV

**Tab 2: Pesquisados (Scraped)**
- Companies found via NIF.pt search
- Basic info: NIF, name, location
- Export: CSV

## 🔧 Commands

### 🚀 Full Automation

```bash
# Run everything with defaults
pt-automate

# Skip specific steps
pt-automate --skip-scrape        # Don't scrape eInforma.pt
pt-automate --skip-search        # Don't search NIF.pt
pt-automate --search-only        # Only search, no enrichment

# Control enrichment
pt-automate --enrich-limit 50    # Enrich max 50 companies
pt-automate --enrich-force       # Re-enrich already enriched

# Custom search keywords
pt-automate --keywords "HOTEL RESTAURANTE TECNOLOGIA"

# More search pages
pt-automate --search-pages 10    # Search 10 pages per keyword
```

**What `pt-automate` does:**
1. Scrapes eInforma.pt for newly registered companies
2. Searches NIF.pt for companies by keyword
3. Enriches companies with contact details (respects API rate limits)
4. Syncs everything to PostgreSQL
5. Shows summary report with stats

**Default search keywords:** TECNOLOGIA, SOFTWARE, CONSULTORIA, CONSTRUCAO

### Individual Commands

```bash
# Scrape eInforma.pt
pt-scrape

# Search NIF.pt
pt-nif-search "RESTAURANTE"
pt-nif-search "HOTEL" --pages 5

# Enrich with contact details
pt-nif-enrich --source historical
pt-enrich-search

# Check API status
pt-nif-enrich --status
```

## 📈 Data Flow

```
eInforma.pt → scraper.py → companies_*.json
                                  ↓
NIF.pt API → nif_enrich.py → companies_enriched.json
                                  ↓
NIF.pt Search → nif_search.py → nif_search_*.json
                                  ↓
Dashboard → app.py + pages/ → Streamlit UI
```

## 🎯 Tips

1. **Bookmark pages:** Use direct URLs to jump to specific pages
2. **Auto-refresh:** Data refreshes every 60 seconds
3. **Rate limits:** NIF.pt API has limits (10/hour, 100/day, 1000/month)
4. **Export:** Download CSV for offline analysis

## 🐛 Troubleshooting

```bash
# Clear cache
pt-dashboard
# Click "🔄 Atualizar Dados" in sidebar

# Restart dashboard
pkill -f streamlit
pt-dashboard
```
