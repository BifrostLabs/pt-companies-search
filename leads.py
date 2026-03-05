#!/usr/bin/env python3
"""
Lead Generation Module
Helps identify and manage potential clients from new company data
"""

import json
import glob
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).parent / "data"
LEADS_FILE = DATA_DIR / "leads_tracking.json"


# Service recommendations based on company type/sector
SERVICES_MAP = {
    "Construção": [
        "🏗️ Contabilidade",
        "📋 Consultoria Fiscal",
        "💼 Seguros Empresariais",
        "📱 Marketing Digital",
        "💻 Infraestrutura de TI",
    ],
    "Tecnologia/TI": [
        "💼 Serviços Jurídicos",
        "📋 Consultoria Fiscal",
        "📈 Consultoria de Crescimento",
        "🎯 Suporte Comercial/BD",
        "🔐 Cibersegurança",
    ],
    "Alimentação/Hospitalidade": [
        "🍽️ Conformidade em Segurança Alimentar",
        "📋 Consultoria Fiscal",
        "📱 Marketing em Redes Sociais",
        "💳 Processamento de Pagamentos",
        "🚚 Software de Logística",
    ],
    "Imobiliário": [
        "📋 Consultoria Fiscal",
        "💼 Serviços Jurídicos",
        "📱 Marketing/Geração de Leads",
        "💻 Software CRM",
        "🖼️ Tours Virtuais/Fotos",
    ],
    "Consultoria": [
        "📋 Consultoria Fiscal",
        "💼 Contratos Jurídicos",
        "📱 Desenvolvimento de Marca",
        "💻 Design de Website",
        "📈 Coaching Empresarial",
    ],
    "Automotivo": [
        "🔧 Gestão de Estoque",
        "📋 Consultoria Fiscal",
        "📱 Publicidade Digital",
        "💳 Soluções de Financiamento",
        "🚗 Gestão de Frotas",
    ],
    "Educação": [
        "📋 Conformidade/Licenciamento",
        "💼 Serviços Jurídicos",
        "📱 Recrutamento de Alunos",
        "💻 LMS/Software",
        "📊 Suporte à Acreditação",
    ],
    "Saúde": [
        "🏥 Conformidade Regulatória",
        "📋 Consultoria Fiscal",
        "💼 Jurídico Médico",
        "📱 Marketing para Pacientes",
        "💻 Gestão de Consultório",
    ],
    "Outro": [
        "📋 Consultoria Fiscal",
        "💼 Serviços Jurídicos",
        "📱 Marketing Digital",
        "💻 Desenvolvimento de Website",
        "📈 Consultoria Empresarial",
    ],
}


# Lead scoring based on company characteristics
def calculate_lead_score(row):
    """Score leads 0-100 based on potential value indicators"""
    score = 50  # Base score
    
    name = row.get("name", "").upper()
    company_type = row.get("type", "Other")
    
    # Boost for company types that typically need more services
    if company_type == "Lda":
        score += 15  # More formal, likely bigger
    elif company_type == "Unipessoal":
        score += 5   # Smaller but still needs services
    
    # Boost for sectors with high service needs
    high_value_keywords = [
        "CONSULT", "GESTÃO", "SOLUTIONS", "SERVICES", "DIGITAL",
        "TECH", "SOFTWARE", "MARKETING", "ENGINEERING", "MEDICAL"
    ]
    for kw in high_value_keywords:
        if kw in name:
            score += 10
            break
    
    # Location-based scoring (Lisbon/Porto = bigger markets)
    # Note: We'd need to enrich data to get location
    
    # Cap at 100
    return min(score, 100)


def get_sector(name):
    """Classify company into sector"""
    name_upper = name.upper()
    sectors = {
        "Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES"],
        "Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA"],
        "Alimentação/Hospitalidade": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO"],
        "Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO"],
        "Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO"],
        "Automotivo": ["AUTO", "CAR ", "VEÍCULOS", "MOTORS"],
        "Educação": ["ACADEMIA", "ESCOLA", "FORMAÇÃO", "EDUCAÇÃO", "ENSINO"],
        "Saúde": ["SAÚDE", "HEALTH", "MÉDIC", "CLÍNIC", "PHARMA"],
    }
    
    for sector, keywords in sectors.items():
        if any(kw in name_upper for kw in keywords):
            return sector
    return "Outro"


def get_company_type(name):
    """Extract company legal type"""
    name_upper = name.upper()
    if "UNIPESSOAL" in name_upper:
        return "Unipessoal"
    elif "LDA" in name_upper:
        return "Lda"
    elif "ASSOCIAÇÃO" in name_upper or "ASSOCIAÇAO" in name_upper:
        return "Associação"
    elif "C.R.L." in name_upper or "CRL" in name_upper:
        return "Cooperativa"
    else:
        return "Outro"


def load_leads_tracking():
    """Load existing lead tracking data"""
    if LEADS_FILE.exists():
        with open(LEADS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_leads_tracking(tracking):
    """Save lead tracking data"""
    LEADS_FILE.parent.mkdir(exist_ok=True)
    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        json.dump(tracking, f, ensure_ascii=False, indent=2)


def update_lead_status(nif, status, notes=""):
    """Update the status of a lead"""
    tracking = load_leads_tracking()
    
    if nif not in tracking:
        tracking[nif] = {
            "status_history": [],
            "notes": []
        }
    
    tracking[nif]["current_status"] = status
    tracking[nif]["last_updated"] = datetime.now().isoformat()
    
    if notes:
        tracking[nif]["notes"].append({
            "date": datetime.now().isoformat(),
            "note": notes
        })
    
    tracking[nif]["status_history"].append({
        "status": status,
        "date": datetime.now().isoformat()
    })
    
    save_leads_tracking(tracking)
    return tracking[nif]


def get_lead_status(nif):
    """Get the current status of a lead"""
    tracking = load_leads_tracking()
    if nif in tracking:
        return tracking[nif].get("current_status", "New")
    return "New"


def enrich_leads_dataframe(df):
    """Add lead generation columns to dataframe"""
    df = df.copy()
    
    df["type"] = df["name"].apply(get_company_type)
    df["sector"] = df["name"].apply(get_sector)
    df["lead_score"] = df.apply(calculate_lead_score, axis=1)
    df["recommended_services"] = df["sector"].map(SERVICES_MAP)
    df["status"] = df["nif"].apply(get_lead_status)
    
    return df


def get_top_leads(df, limit=20):
    """Get top scored leads"""
    enriched = enrich_leads_dataframe(df)
    return enriched.sort_values("lead_score", ascending=False).head(limit)


def export_for_outreach(df, format="csv"):
    """Export leads for outreach campaigns"""
    enriched = enrich_leads_dataframe(df)
    
    # Filter only new leads (not contacted yet)
    new_leads = enriched[enriched["status"] == "New"]
    
    export_df = new_leads[[
        "nif", "name", "date", "sector", "type", "lead_score", "url"
    ]].copy()
    
    export_df.columns = [
        "NIF", "Company Name", "Registration Date", "Sector", 
        "Type", "Lead Score", "Profile URL"
    ]
    
    return export_df.sort_values("Lead Score", ascending=False)


if __name__ == "__main__":
    # Test the module
    files = sorted(glob.glob(str(DATA_DIR / "companies_*.json")), reverse=True)
    if files:
        files = [f for f in files if "_enriched" not in f]
        with open(files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        
        df = pd.DataFrame(data["companies"])
        top_leads = get_top_leads(df, limit=10)
        
        print("🎯 TOP 10 LEADS:")
        print("-" * 80)
        for _, row in top_leads.iterrows():
            print(f"Score: {row['lead_score']:3d} | {row['sector']:15s} | {row['name'][:50]}")
