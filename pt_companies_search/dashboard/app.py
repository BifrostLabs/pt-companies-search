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
        get_source_stats, get_region_stats, is_db_available
    )
except ImportError as e:
    print(f"Import Error: {e}. Check directory structure and PYTHONPATH.")

app = FastAPI(title="PT Companies Dashboard")

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
        "version": "3.0.0-fastapi-tailwind",
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

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    if not check_auth(request):
        return RedirectResponse(url="/login", status_code=302)
    
    db_available = test_connection()
    stats = get_contact_coverage() if db_available else {}
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "db_available": db_available,
        "stats": stats
    })

@app.get("/api/data")
def get_dashboard_data(request: Request):
    if not check_auth(request):
        raise HTTPException(status_code=401, detail="Unauthorized")

    sectors = get_sector_stats()
    regions = get_region_stats()
    
    # Use Polars for efficient data transformation
    if sectors:
        df_sector = pl.DataFrame(sectors).head(8).to_dicts()
    else:
        df_sector = []
        
    if regions:
        df_region = pl.DataFrame(regions).head(10).to_dicts()
    else:
        df_region = []
        
    return {
        "sectors": df_sector,
        "regions": df_region
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8501)
