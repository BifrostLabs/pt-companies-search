#!/usr/bin/env python3
"""
eInforma.pt - Novas Empresas
"""

import json
import glob
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Config
DATA_DIR = Path(__file__).parent.parent / "data"

# Standard sector definitions (same as NIF.pt page)
SECTORS = {
    "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL"],
    "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS"],
    "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO"],
    "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO", "MEDIÇÃO IMOBILIÁRIA"],
    "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA"],
}


def get_sector(name):
    """Classify company into sector"""
    name_upper = name.upper()
    for sector, keywords in SECTORS.items():
        if any(kw in name_upper for kw in keywords):
            return sector
    return "Outro"


@st.cache_data(ttl=60)
def load_data():
    """Load the latest company data"""
    files = sorted(glob.glob(str(DATA_DIR / "companies_*.json")), reverse=True)
    if not files:
        return None, None
    
    # Exclude enriched and historical files
    files = [f for f in files if "_enriched" not in f and "_historical" not in f]
    if not files:
        return None, None
    
    latest = files[0]
    with open(latest, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data, latest


@st.cache_data(ttl=60)
def load_historical_data():
    """Load accumulated historical data"""
    historical_file = DATA_DIR / "companies_historical.json"
    if historical_file.exists():
        with open(historical_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


@st.cache_data(ttl=60)
def load_enriched_data():
    """Load enriched company data from NIF.pt API"""
    enriched_file = DATA_DIR / "companies_enriched.json"
    if enriched_file.exists():
        with open(enriched_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("companies", {})
    return {}


def merge_enriched_data(df, enriched_dict):
    """Merge enriched data into dataframe"""
    if not enriched_dict:
        return df
    
    enriched_rows = []
    for nif, enriched in enriched_dict.items():
        row = {"nif": nif}
        for key in ["address", "city", "postal_code", "phone", "email", "website", 
                    "cae", "activity", "status", "region", "county", "parish"]:
            row[f"enriched_{key}"] = enriched.get(key)
        enriched_rows.append(row)
    
    if not enriched_rows:
        return df
    
    enriched_df = pd.DataFrame(enriched_rows)
    return df.merge(enriched_df, on="nif", how="left")


def render_compact_sidebar(df, enriched_data, has_historical):
    """Render compact sidebar filters"""
    
    # Data source (if historical available)
    use_historical = False
    selected_year = "Todos os Anos"
    
    if has_historical:
        st.sidebar.markdown("**📚 Fonte**")
        data_source = st.sidebar.radio(
            "Fonte",
            ["Recentes", "Histórico"],
            horizontal=True,
            label_visibility="collapsed"
        )
        use_historical = data_source == "Histórico"
        
        if use_historical:
            available_years = sorted(df["date_obj"].dropna().apply(lambda x: x.year).unique(), reverse=True)
            if available_years:
                selected_year = st.sidebar.selectbox(
                    "Ano",
                    ["Todos"] + [str(y) for y in available_years],
                    label_visibility="collapsed"
                )
    
    # Search
    st.sidebar.markdown("**🔍 Buscar**")
    search = st.sidebar.text_input("Buscar", "", placeholder="Nome da empresa...", label_visibility="collapsed").strip().lower()
    
    # Date filter (compact)
    st.sidebar.markdown("**📅 Data**")
    min_date = df["date_obj"].min()
    max_date = df["date_obj"].max()
    date_range = st.sidebar.date_input(
        "Período",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
        label_visibility="collapsed"
    )
    
    # Enriched filter
    show_enriched_only = False
    if enriched_data:
        st.sidebar.markdown("**📊 Dados**")
        enriched_count = len([nif for nif in df["nif"] if nif in enriched_data])
        show_enriched_only = st.sidebar.checkbox(f"Apenas enriquecidas ({enriched_count})")
    
    # Sector filter - multiselect (compact)
    st.sidebar.markdown("**🏢 Setor**")
    selected_sectors = st.sidebar.multiselect(
        "Setor",
        list(SECTORS.keys()),
        label_visibility="collapsed",
        placeholder="Todos os setores"
    )
    
    # Export section
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📥 Exportar**")
    
    return {
        "search": search,
        "date_range": date_range,
        "show_enriched_only": show_enriched_only,
        "sectors": selected_sectors,
        "use_historical": use_historical,
        "selected_year": selected_year
    }


def apply_filters(df, filters, enriched_data):
    """Apply filters to dataframe"""
    filtered_df = df.copy()
    
    # Date filter
    date_range = filters["date_range"]
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
        filtered_df = filtered_df[
            (filtered_df["date_obj"] >= start_date) & 
            (filtered_df["date_obj"] <= end_date)
        ]
    
    # Search filter
    if filters["search"]:
        filtered_df = filtered_df[filtered_df["name"].str.lower().str.contains(filters["search"], na=False)]
    
    # Sector filter
    if filters["sectors"]:
        all_keywords = []
        for sector in filters["sectors"]:
            all_keywords.extend(SECTORS.get(sector, []))
        if all_keywords:
            mask = filtered_df["name"].str.upper().apply(
                lambda x: any(kw in str(x).upper() for kw in all_keywords)
            )
            filtered_df = filtered_df[mask]
    
    # Enriched filter
    if filters["show_enriched_only"] and enriched_data:
        enriched_nifs = set(enriched_data.keys())
        filtered_df = filtered_df[filtered_df["nif"].isin(enriched_nifs)]
    
    return filtered_df


def main():
    # Center content
    _, col_main, _ = st.columns([0.05, 0.9, 0.05])
    
    with col_main:
        st.title("📋 eInforma.pt - Novas Empresas")
        st.markdown("Empresas recém-registradas em Portugal")
        
        st.markdown("---")
        
        # Load data
        data, data_file = load_data()
        
        if not data:
            st.error("Nenhum dado encontrado. Execute `pt-scrape` primeiro.")
            st.stop()
        
        companies = data["companies"]
        df = pd.DataFrame(companies)
        df["date_obj"] = pd.to_datetime(df["date"], format="%d-%m-%Y").dt.date
        
        # Load enriched data
        enriched_data = load_enriched_data()
        if enriched_data:
            df = merge_enriched_data(df, enriched_data)
        
        # Check for historical data
        historical_data = load_historical_data()
        has_historical = historical_data and historical_data.get("companies")
        
        # Render sidebar
        filters = render_compact_sidebar(df, enriched_data, has_historical)
        
        # Handle historical data selection
        if filters["use_historical"] and has_historical:
            hist_companies = list(historical_data["companies"].values())
            df = pd.DataFrame(hist_companies)
            df["date_obj"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce").dt.date
            
            if filters["selected_year"] != "Todos":
                year_int = int(filters["selected_year"])
                df = df[df["date_obj"].apply(lambda x: x.year if pd.notna(x) else 0) == year_int]
            
            if enriched_data:
                df = merge_enriched_data(df, enriched_data)
        
        # Apply filters
        filtered_df = apply_filters(df, filters, enriched_data)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(df))
        with col2:
            st.metric("Filtradas", len(filtered_df))
        with col3:
            st.metric("Datas", df["date"].nunique())
        with col4:
            if enriched_data:
                enriched_count = len([nif for nif in filtered_df["nif"] if nif in enriched_data])
                st.metric("Enriquecidas", enriched_count)
            else:
                st.metric("Atualizado", data.get("fetch_date", "N/A")[:10])
        
        st.markdown("---")
        
        # Display
        view_mode = st.radio("Visualização", ["Tabela", "Cartões"], horizontal=True)
        
        if view_mode == "Tabela":
            base_cols = ["date", "nif", "name"]
            display_df = filtered_df[base_cols].copy()
            display_df.columns = ["Data", "NIF", "Empresa"]
            
            if "enriched_phone" in filtered_df.columns:
                display_df["📞"] = filtered_df["enriched_phone"]
            if "enriched_email" in filtered_df.columns:
                display_df["✉️"] = filtered_df["enriched_email"]
            if "enriched_city" in filtered_df.columns:
                display_df["📍"] = filtered_df["enriched_city"]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=600,
                column_config={
                    "NIF": st.column_config.TextColumn("NIF", width="small"),
                    "Empresa": st.column_config.TextColumn("Empresa", width="large"),
                }
            )
        else:
            for _, row in filtered_df.head(100).iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.markdown(f"**{row['name']}**")
                    with col2:
                        st.markdown(f"📅 {row['date']}")
                    with col3:
                        st.markdown(f"[🔗 {row['nif']}]({row['url']})")
                    
                    enriched_info = []
                    if "enriched_phone" in row and pd.notna(row.get("enriched_phone")):
                        enriched_info.append(f"📞 {row['enriched_phone']}")
                    if "enriched_email" in row and pd.notna(row.get("enriched_email")):
                        enriched_info.append(f"✉️ {row['enriched_email']}")
                    if "enriched_city" in row and pd.notna(row.get("enriched_city")):
                        enriched_info.append(f"📍 {row['enriched_city']}")
                    
                    if enriched_info:
                        st.caption(" | ".join(enriched_info))
                    
                    st.markdown("---")
    
    # Sidebar export (outside main column)
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        "📄 CSV",
        csv,
        f"empresas_einforma_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )
    
    # Refresh button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"📅 {datetime.now().strftime('%d/%m %H:%M')}")
    st.sidebar.caption("[eInforma.pt](https://www.einforma.pt)")


# Run main when page is loaded
main()
