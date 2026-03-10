# 🇵🇹 Portugal New Companies Dashboard

A full-stack, real-time dashboard and data pipeline for tracking new Portuguese company registrations. 

## 🏗️ Architecture & Tech Stack

This project was recently refactored from Streamlit to a modern, highly-performant web stack:

- **Backend:** FastAPI, Python 3.13, Uvicorn
- **Frontend:** Vanilla JS, HTML5, Tailwind CSS (via CDN), Chart.js
- **Data Engine:** Polars (for lightning-fast DataFrame aggregations)
- **Database:** PostgreSQL (with ADBC drivers)
- **Security:** HTTPOnly Cookies with Bearer Token (`ADMIN_TOKEN`) protection on all routes and APIs.
- **Infrastructure:** Docker, Kubernetes (k3s), Helm, ArgoCD, GitHub Actions

## 📂 Project Structure

```
pt-new-companies/
├── pt_companies_search/
│   ├── dashboard/
│   │   ├── app.py             # FastAPI entry point & API routes
│   │   └── templates/         # Jinja2 HTML + Tailwind templates
│   │       ├── login.html     # Secure authentication gate
│   │       ├── dashboard.html # Main metrics and Chart.js graphs
│   │       ├── einforma.html  # Raw eInforma registration data
│   │       └── nif.html       # Enriched contact & sector data
│   ├── core/                  # Database connections & Polars logic
│   └── scrapers/              # eInforma & NIF.pt scrapers
├── docker/                    # Dockerfiles for microservices
├── pyproject.toml             # Project dependencies
└── aliases.sh                 # CLI commands for automation
```

## 🔒 Security & Authentication

All UI routes and JSON endpoints are protected by a global `ADMIN_TOKEN`. 
Unauthenticated requests to `/` or any `/api/*` endpoint will be rejected (401) or redirected (302) to the `/login` portal.

The current token is injected securely via Kubernetes Secrets/Helm values and stored in an `HTTPOnly`, `SameSite=Lax` browser cookie upon login.

## 🌐 Endpoints

- **`GET /login`** - Authentication portal
- **`GET /`** - Main dashboard (Requires Auth)
- **`GET /einforma`** - eInforma directory table (Requires Auth)
- **`GET /nif`** - NIF.pt enriched database table (Requires Auth)
- **`GET /api/data`** - Polars-aggregated metrics for Chart.js (Requires Auth)

## 🚀 Quick Start (CLI Automation)

To manually trigger the scraping and enrichment pipelines from the terminal:

```bash
# Load aliases
source /root/.openclaw/workspace/pt-new-companies/aliases.sh

# 🎯 ONE COMMAND TO DO EVERYTHING:
pt-automate              # Scrape + Search + Enrich + Sync to DB

# Or run individual steps:
pt-scrape                # Fetch from eInforma.pt
pt-nif-search "HOTEL"    # Query NIF.pt database
pt-nif-enrich            # Enrich scraped companies via NIF API
```

## 📊 Data Flow

1. **Scraping:** Automated jobs fetch the latest registrations from `eInforma.pt`.
2. **Enrichment:** `NIF.pt` API is queried to find contacts (phone, email), sectors (CAE), and locations.
3. **Storage:** JSON state is synced robustly to a PostgreSQL database.
4. **Aggregation:** FastAPI uses `Polars` to query PostgreSQL and structure the data efficiently.
5. **Presentation:** Tailwind CSS and Chart.js render the JSON payloads dynamically in the browser.

## 🎯 Tips & Limits

- **Rate Limits:** The NIF.pt Free API enforces strict limits (10/hour, 100/day, 1000/month). `pt-automate` naturally respects these limits and persists its queue state.
- **Auto-deployment:** Commits to `main` are automatically built by GitHub Actions and synced to the cluster via ArgoCD.
