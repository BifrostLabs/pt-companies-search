import csv
import io
import logging
import os
import time
from datetime import datetime
from typing import Annotated, Optional

import polars as pl
from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from pt_companies_search.core.database import (
    get_contact_coverage,
    get_einforma_dataframe,
    get_enriched_dataframe,
    get_lead_status_stats,
    get_leads,
    get_nif_coverage,
    get_region_stats,
    get_search_dataframe,
    get_sector_stats,
    test_connection,
    update_lead_status,
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pt-dashboard")

app = FastAPI(title="PT Companies Dashboard", docs_url=None, redoc_url=None)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "changeme")
AUTH_COOKIE = "pt_auth_token"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def log_request_time(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    elapsed = time.time() - t0
    logger.info("%-40s %dms", request.url.path, elapsed * 1000)
    response.headers["X-Process-Time"] = f"{elapsed:.4f}"
    return response


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _is_authenticated(request: Request) -> bool:
    token = request.cookies.get(AUTH_COOKIE)
    return bool(token and token == ADMIN_TOKEN)


def require_api_auth(request: Request) -> None:
    """Dependency for JSON API routes — raises 401 if not authenticated."""
    if not _is_authenticated(request):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


ApiAuth = Annotated[None, Depends(require_api_auth)]


# ---------------------------------------------------------------------------
# Public routes
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "db": "connected" if test_connection() else "disconnected",
        "version": "3.2.0",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if _is_authenticated(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, token: str = Form(...)):
    if token == ADMIN_TOKEN:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(AUTH_COOKIE, token, httponly=True, max_age=86400, samesite="lax")
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid token."})


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(AUTH_COOKIE)
    return response


# ---------------------------------------------------------------------------
# Protected HTML pages  (redirect to /login when not authenticated)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    stats = get_contact_coverage() if test_connection() else {}
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "db_available": test_connection(),
        "stats": stats,
        "active_page": "dashboard",
    })


@app.get("/einforma", response_class=HTMLResponse)
def einforma_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("einforma.html", {"request": request, "active_page": "einforma"})


@app.get("/nif", response_class=HTMLResponse)
def nif_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("nif.html", {"request": request, "active_page": "nif"})


@app.get("/leads", response_class=HTMLResponse)
def leads_page(request: Request):
    if not _is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("leads.html", {"request": request, "active_page": "leads"})


# ---------------------------------------------------------------------------
# Protected JSON API
# ---------------------------------------------------------------------------

@app.get("/api/data")
def get_dashboard_data(_: ApiAuth):
    sectors = get_sector_stats()
    regions = get_region_stats()
    return {
        "sectors": pl.DataFrame(sectors).head(8).to_dicts() if sectors else [],
        "regions": pl.DataFrame(regions).head(10).to_dicts() if regions else [],
    }


@app.get("/api/einforma")
def get_einforma_data(_: ApiAuth):
    try:
        return get_einforma_dataframe().fill_null("").to_dicts()
    except Exception:
        return []


@app.get("/api/nif/enriched")
def get_nif_enriched_data(_: ApiAuth):
    try:
        return get_enriched_dataframe().fill_null("").to_dicts()
    except Exception:
        return []


@app.get("/api/nif/searched")
def get_nif_searched_data(_: ApiAuth):
    try:
        return get_search_dataframe().fill_null("").to_dicts()
    except Exception:
        return []


@app.get("/api/nif/coverage")
def get_nif_coverage_stats(_: ApiAuth):
    try:
        return get_nif_coverage()
    except Exception as e:
        logger.error("Coverage stats error: %s", e)
        return {"enriched": {}, "searched": {}}


@app.get("/api/leads")
def get_leads_data(
    _: ApiAuth,
    status: Optional[str] = None,
    sector: Optional[str] = None,
    region: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
):
    try:
        leads = get_leads(
            lead_status=status or None,
            sector=sector or None,
            region=region or None,
            query=q or None,
            limit=limit,
            offset=offset,
        )
        for lead in leads:
            for k, v in lead.items():
                if hasattr(v, "isoformat"):
                    lead[k] = v.isoformat()
        return leads
    except Exception as e:
        logger.error("Leads fetch error: %s", e)
        return []


@app.get("/api/leads/stats")
def get_leads_stats(_: ApiAuth):
    try:
        return get_lead_status_stats()
    except Exception:
        return {}


@app.patch("/api/leads/{nif}/status")
async def patch_lead_status(nif: str, request: Request, _: ApiAuth):
    body = await request.json()
    status_val = body.get("status")
    notes = body.get("notes")
    if not status_val:
        raise HTTPException(status_code=400, detail="status is required")
    if not update_lead_status(nif, status_val, notes):
        raise HTTPException(status_code=400, detail="Invalid status or NIF not found")
    return {"ok": True}


@app.get("/api/leads/export")
def export_leads_csv(
    _: ApiAuth,
    status: Optional[str] = None,
    sector: Optional[str] = None,
    region: Optional[str] = None,
):
    leads = get_leads(
        lead_status=status or None,
        sector=sector or None,
        region=region or None,
        limit=10000,
    )
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found")

    fields = ["nif", "name", "phone", "email", "website", "city", "region",
              "sector", "cae", "capital", "registration_date", "lead_status", "lead_notes"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for lead in leads:
        writer.writerow({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in lead.items()})

    output.seek(0)
    filename = f"pt_leads_{datetime.now().strftime('%Y%m%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
