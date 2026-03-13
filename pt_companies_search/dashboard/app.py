import os
import polars as pl
from datetime import datetime
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from pt_companies_search.core.database import (
        test_connection, get_contact_coverage, get_sector_stats,
        get_source_stats, get_region_stats, is_db_available,
        get_einforma_dataframe, get_enriched_dataframe, get_search_dataframe
    )
except ImportError as e:
    print(f"Import Error: {e}. Check directory structure and PYTHONPATH.")

app = FastAPI(title="PT Companies Dashboard")

import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pt-dashboard")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"PATH: {request.url.path} | TIME: {process_time:.4f}s")
    response.headers["X-Process-Time"] = str(process_time)
    return response


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "changeme")
AUTH_COOKIE_NAME = "pt_auth_token"

def check_auth(request: Request):
    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token or token != ADMIN_TOKEN:
        return False
    return True

@app.get("/health")
def health_check():
    db_status = "connected" if test_connection() else "disconnected"
    return {
        "status": "healthy",
        "db": db_status,
        "version": "3.1.0-fastapi-tailwind",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if check_auth(request):
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, token: str = Form(...)):
    if token == ADMIN_TOKEN:
        response = RedirectResponse(url="/", status_code=302)
        response.set_cookie(key=AUTH_COOKIE_NAME, value=token, httponly=True, max_age=86400, samesite="lax")
        return response
    return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid token. Please try again."})

@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(AUTH_COOKIE_NAME)
    return response

# --- Protected HTML Pages ---

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    
    db_available = test_connection()
    stats = get_contact_coverage() if db_available else {}
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "db_available": db_available,
        "stats": stats,
        "active_page": "dashboard"
    })

@app.get("/einforma", response_class=HTMLResponse)
def einforma_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("einforma.html", {"request": request, "active_page": "einforma"})

@app.get("/nif", response_class=HTMLResponse)
def nif_page(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("nif.html", {"request": request, "active_page": "nif"})

# --- Protected Data APIs ---

@app.get("/api/data")
def get_dashboard_data(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    sectors = get_sector_stats()
    regions = get_region_stats()
    
    df_sector = pl.DataFrame(sectors).head(8).to_dicts() if sectors else []
    df_region = pl.DataFrame(regions).head(10).to_dicts() if regions else []
        
    return {"sectors": df_sector, "regions": df_region}

@app.get("/api/einforma")
def get_einforma_data(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        df = get_einforma_dataframe()
        # Ensure dates are serialized properly; fill nulls
        return df.fill_null("").to_dicts()
    except Exception as e:
        return []

@app.get("/api/nif/enriched")
def get_nif_enriched_data(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        df = get_enriched_dataframe()
        return df.fill_null("").to_dicts()
    except Exception as e:
        return []

@app.get("/api/nif/searched")
def get_nif_searched_data(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        df = get_search_dataframe()
        return df.fill_null("").to_dicts()
    except Exception as e:
        return []

@app.get("/api/nif/coverage")
def get_nif_coverage_stats(request: Request):
    """Get phone, email, website coverage statistics"""
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        with get_cursor() as cur:
            # Get coverage for enriched companies
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE phone IS NOT NULL) as with_phone,
                    COUNT(*) FILTER (WHERE email IS NOT NULL) as with_email,
                    COUNT(*) FILTER (WHERE website IS NOT NULL) as with_website,
                    COUNT(*) FILTER (WHERE phone IS NOT NULL OR email IS NOT NULL OR website IS NOT NULL) as with_any_contact
                FROM companies 
                WHERE source = 'nif_api' AND enriched_at IS NOT NULL
            """)
            enriched = dict(cur.fetchone())
            
            # Get coverage for searched companies
            cur.execute("""
                SELECT 
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE phone IS NOT NULL) as with_phone,
                    COUNT(*) FILTER (WHERE email IS NOT NULL) as with_email,
                    COUNT(*) FILTER (WHERE website IS NOT NULL) as with_website,
                    COUNT(*) FILTER (WHERE phone IS NOT NULL OR email IS NOT NULL OR website IS NOT NULL) as with_any_contact
                FROM companies 
                WHERE source = 'nif_search'
            """)
            searched = dict(cur.fetchone())
            
            # Calculate percentages
            def calc_pct(stats):
                total = stats['total'] or 0
                if total == 0:
                    return {**stats, 'phone_pct': 0, 'email_pct': 0, 'website_pct': 0, 'contact_pct': 0}
                return {
                    **stats,
                    'phone_pct': round((stats['with_phone'] or 0) / total * 100, 1),
                    'email_pct': round((stats['with_email'] or 0) / total * 100, 1),
                    'website_pct': round((stats['with_website'] or 0) / total * 100, 1),
                    'contact_pct': round((stats['with_any_contact'] or 0) / total * 100, 1)
                }
            
            return {
                'enriched': calc_pct(enriched),
                'searched': calc_pct(searched)
            }
    except Exception as e:
        print(f"Error getting coverage stats: {e}")
        return {'enriched': {}, 'searched': {}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
