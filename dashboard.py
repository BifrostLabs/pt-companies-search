#!/usr/bin/env python3
"""
Portugal New Companies Dashboard
Streamlit app to visualize newly registered companies
"""

import json
import glob
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent))
from leads import (
    enrich_leads_dataframe, 
    update_lead_status, 
    get_lead_status,
    load_leads_tracking,
    SERVICES_MAP
)

# Config
DATA_DIR = Path(__file__).parent / "data"
st.set_page_config(
    page_title="Novas Empresas Portugal",
    page_icon="🇵🇹",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    /* Total Companies metric - highlight style */
    div[data-testid="stMetric"]:first-child {
        background-color: #1e3a5f !important;
    }
    
    div[data-testid="stMetric"]:first-child label {
        color: #ffffff !important;
    }
    
    div[data-testid="stMetric"]:first-child [data-testid="stMetricValue"] {
        color: #ffd700 !important;
    }
    
    /* Other metrics */
    .stMetric {
        padding: 15px;
        border-radius: 8px;
    }
    
    .company-card {
        padding: 10px;
        border-left: 3px solid #FF4B4B;
        margin-bottom: 10px;
        background-color: #f9f9f9;
    }
    
    .nif-link a {
        color: #FF4B4B;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


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


@st.cache_data(ttl=60)
def load_nif_search_results():
    """Load NIF.pt search results"""
    import glob
    
    search_files = sorted(glob.glob(str(DATA_DIR / "nif_search_*.json")), reverse=True)
    if not search_files:
        return []
    
    all_companies = []
    for search_file in search_files:
        with open(search_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            all_companies.extend(data.get("companies", []))
    
    # Remove duplicates by NIF
    unique_companies = {}
    for company in all_companies:
        nif = company.get("nif")
        if nif and nif not in unique_companies:
            unique_companies[nif] = company
    
    return list(unique_companies.values())


def merge_enriched_data(df, enriched_dict):
    """Merge enriched data into dataframe"""
    if not enriched_dict:
        return df
    
    # Create a mapping of NIF to enriched data
    enriched_rows = []
    for nif, enriched in enriched_dict.items():
        row = {"nif": nif}
        # Add enriched columns
        for key in ["address", "city", "postal_code", "phone", "email", "website", 
                    "cae", "activity", "status", "region", "county", "parish"]:
            row[f"enriched_{key}"] = enriched.get(key)
        enriched_rows.append(row)
    
    if not enriched_rows:
        return df
    
    enriched_df = pd.DataFrame(enriched_rows)
    
    # Merge with original dataframe
    df = df.merge(enriched_df, on="nif", how="left")
    
    return df


def show_einforma_page():
    """Show eInforma.pt data page"""
    st.title("🇵🇹 Portugal - Novas Empresas (eInforma.pt)")
    st.markdown("Empresas recém-registradas em Portugal")
    
    # Load data
    data, data_file = load_data()
    
    if not data:
        st.error("Nenhum dado encontrado. Execute `python3 scraper.py` primeiro.")
        st.stop()
    
    companies = data["companies"]
    df = pd.DataFrame(companies)
    
    # Convert date strings to date objects for filtering
    df["date_obj"] = pd.to_datetime(df["date"], format="%d-%m-%Y").dt.date
    
    # Load and merge enriched data from NIF.pt
    enriched_data = load_enriched_data()
    if enriched_data:
        df = merge_enriched_data(df, enriched_data)
    
    # Historical data option
    historical_data = load_historical_data()
    use_historical = False
    selected_year = None
    
    if historical_data and historical_data.get("companies"):
        st.sidebar.markdown("### 📚 Fonte de Dados")
        data_source = st.sidebar.radio(
            "Selecione a fonte de dados",
            ["Recentes (7 dias)", "Histórico (acumulado)"],
            horizontal=True,
            key="data_source_selector"
        )
        use_historical = data_source == "Histórico (acumulado)"
        
        if use_historical:
            # Load historical data
            hist_companies = list(historical_data["companies"].values())
            df = pd.DataFrame(hist_companies)
            
            # Parse dates
            df["date_obj"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce").dt.date
            
            # Year filter for historical data
            available_years = sorted(df["date_obj"].dropna().apply(lambda x: x.year).unique(), reverse=True)
            
            if available_years:
                st.sidebar.markdown("### 📅 Filtrar por Ano")
                selected_year = st.sidebar.selectbox(
                    "Selecione o Ano",
                    ["Todos os Anos"] + [str(y) for y in available_years]
                )
                
                if selected_year != "Todos os Anos":
                    year_int = int(selected_year)
                    df = df[df["date_obj"].apply(lambda x: x.year if pd.notna(x) else 0) == year_int]
            
            # Show historical stats
            st.sidebar.markdown("---")
            st.sidebar.markdown(f"**📊 Estatísticas Históricas**")
            st.sidebar.caption(f"Total único: {len(historical_data['companies'])}")
            if historical_data["metadata"].get("last_updated"):
                st.sidebar.caption(f"Última atualização: {historical_data['metadata']['last_updated'][:10]}")
    
    # Sidebar filters
    st.sidebar.header("⚙️ Filtros")
    
    # Date filter - date picker
    min_date = df["date_obj"].min()
    max_date = df["date_obj"].max()
    
    selected_date_range = st.sidebar.date_input(
        "Data de Registro",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )
    
    # Handle single date or range
    if isinstance(selected_date_range, tuple):
        if len(selected_date_range) == 2:
            start_date, end_date = selected_date_range
        else:
            start_date = end_date = selected_date_range[0]
    else:
        start_date = end_date = selected_date_range
    
    # Search
    search = st.sidebar.text_input("🔍 Buscar empresa", "").strip().lower()
    
    # Enriched filter
    st.sidebar.markdown("---")
    if enriched_data:
        enriched_count = len([nif for nif in df["nif"] if nif in enriched_data])
        show_enriched_only = st.sidebar.checkbox(
            f"📊 Apenas Enriquecidas ({enriched_count})",
            help="Mostrar apenas empresas com dados enriquecidos do NIF.pt"
        )
    else:
        show_enriched_only = False
        st.sidebar.info("💡 Execute `pt-nif-enrich` para enriquecer dados")
    
    # Sector filters
    st.sidebar.markdown("### 🏢 Filtros por Setor")
    sectors = {
        "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES"],
        "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "IT ", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA"],
        "🍽️ Alimentação/Hospitalidade": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO"],
        "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO"],
        "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVICES", "SERVIÇOS", "GESTÃO"],
        "🚗 Automotivo": ["AUTO", "CAR ", "VEÍCULOS", "MOTORS"],
        "🎓 Educação": ["ACADEMIA", "ESCOLA", "FORMAÇÃO", "EDUCAÇÃO", "ENSINO"],
        "🏥 Saúde": ["SAÚDE", "HEALTH", "MÉDIC", "CLÍNIC", "PHARMA"],
    }
    
    selected_sectors = []
    for sector, keywords in sectors.items():
        if st.sidebar.checkbox(sector):
            selected_sectors.extend(keywords)
    
    # Apply filters
    filtered_df = df.copy()
    
    # Date filter
    if start_date and end_date:
        filtered_df = filtered_df[
            (filtered_df["date_obj"] >= start_date) & 
            (filtered_df["date_obj"] <= end_date)
        ]
    
    if search:
        filtered_df = filtered_df[filtered_df["name"].str.lower().str.contains(search)]
    
    if selected_sectors:
        mask = filtered_df["name"].str.upper().apply(
            lambda x: any(kw in x for kw in selected_sectors)
        )
        filtered_df = filtered_df[mask]
    
    # Enriched-only filter
    if show_enriched_only and enriched_data:
        enriched_nifs = set(enriched_data.keys())
        filtered_df = filtered_df[filtered_df["nif"].isin(enriched_nifs)]
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    data_label = "Histórico" if use_historical else "Total"
    
    with col1:
        st.metric(f"Empresas {data_label}", len(df))
    with col2:
        st.metric("Filtradas", len(filtered_df))
    with col3:
        st.metric("Datas Cobertas", df["date"].nunique())
    with col4:
        if use_historical and historical_data:
            st.metric("Total Acumulado", len(historical_data["companies"]))
        else:
            st.metric("Última Atualização", data.get("fetch_date", "N/A")[:10])
    
    st.markdown("---")
    
    # Display options
    col_view1, col_view2 = st.columns([3, 1])
    with col_view2:
        view_mode = st.radio("Visualização", ["Tabela", "Cartões"], horizontal=True)
    
    if view_mode == "Tabela":
        # Interactive table - show enriched data if available
        base_cols = ["date", "nif", "name"]
        display_df = filtered_df[base_cols].copy()
        display_df.columns = ["Data", "NIF", "Nome da Empresa"]
        
        # Add enriched columns if available
        enriched_cols = []
        if "enriched_phone" in filtered_df.columns:
            enriched_cols.append("enriched_phone")
            display_df["Telefone"] = filtered_df["enriched_phone"]
        if "enriched_email" in filtered_df.columns:
            enriched_cols.append("enriched_email")
            display_df["Email"] = filtered_df["enriched_email"]
        if "enriched_city" in filtered_df.columns:
            enriched_cols.append("enriched_city")
            display_df["Cidade"] = filtered_df["enriched_city"]
        
        # Show enrichment status
        if enriched_cols:
            st.caption(f"📊 {len(filtered_df[filtered_df[enriched_cols[0]].notna()])} empresas com dados enriquecidos")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=600,
            column_config={
                "NIF": st.column_config.TextColumn("NIF", width="small"),
                "Nome da Empresa": st.column_config.TextColumn("Nome da Empresa", width="large"),
            }
        )
    elif view_mode == "Cartões":
        # Card view with enriched data
        for _, row in filtered_df.head(100).iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{row['name']}**")
                with col2:
                    st.markdown(f"📅 {row['date']}")
                with col3:
                    st.markdown(f"[🔗 {row['nif']}]({row['url']})")
                
                # Show enriched data if available
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
    
    # Export
    st.sidebar.markdown("---")
    st.sidebar.subheader("📥 Exportar")
    
    col_exp1, col_exp2 = st.sidebar.columns(2)
    
    with col_exp1:
        # CSV export
        csv = filtered_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📄 CSV",
            csv,
            f"empresas_portugal_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv"
        )
    
    with col_exp2:
        # JSON export - exclude date_obj column
        export_df = filtered_df.drop(columns=["date_obj"], errors="ignore")
        json_data = json.dumps(export_df.to_dict("records"), indent=2, ensure_ascii=False, default=str)
        st.download_button(
            "📋 JSON",
            json_data,
            f"empresas_portugal_{datetime.now().strftime('%Y%m%d')}.json",
            "application/json"
        )
    
    # Refresh button
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Atualizar Dados", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    # Enrichment status
    if enriched_data:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Enriquecimento")
        enriched_count = len(filtered_df[filtered_df["enriched_phone"].notna()]) if "enriched_phone" in filtered_df.columns else 0
        st.sidebar.metric("Empresas Enriquecidas", enriched_count)
        if enriched_count > 0:
            st.sidebar.caption(f"via [NIF.pt](https://www.nif.pt/api/)")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.caption(f"Fonte de dados: [eInforma.pt](https://www.einforma.pt/novas-empresas-portuguesas)")
    st.sidebar.caption(f"Arquivo: `{Path(data_file).name}`")


def show_nif_page():
    """Show NIF.pt data page with enriched and search results"""
    st.title("📊 Dados NIF.pt")
    
    # Load data
    enriched_data = load_enriched_data()
    search_results = load_nif_search_results()
    
    # Tabs
    tab1, tab2 = st.tabs(["📊 Enriquecidos (API)", "🔍 Pesquisados (Scraped)"])
    
    # ==================== TAB 1: ENRICHED DATA ====================
    with tab1:
        st.markdown("Dados de contacto obtidos via [NIF.pt API](https://www.nif.pt/api/)")
        
        if not enriched_data:
            st.info("💡 Nenhum dado enriquecido encontrado. Execute `pt-nif-enrich` para enriquecer empresas.")
            st.code("pt-nif-enrich --source historical", language="bash")
        else:
            # Convert to dataframe
            enriched_list = []
            for nif, data in enriched_data.items():
                row = {"nif": nif}
                row["name"] = data.get("name") or data.get("title", "Unknown")
                row["date"] = data.get("date", "N/A")
                row["url"] = data.get("url", f"https://www.nif.pt/{nif}/")
                row["phone"] = data.get("phone")
                row["email"] = data.get("email")
                row["website"] = data.get("website")
                row["city"] = data.get("city")
                row["region"] = data.get("region")
                enriched_list.append(row)
            
            df = pd.DataFrame(enriched_list)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Enriquecidas", len(df))
            with col2:
                with_phone = len(df[df["phone"].notna()])
                st.metric("📞 Com Telefone", with_phone)
            with col3:
                with_email = len(df[df["email"].notna()])
                st.metric("✉️ Com Email", with_email)
            with col4:
                with_website = len(df[df["website"].notna()])
                st.metric("🌐 Com Website", with_website)
            
            st.markdown("---")
            
            # Filters
            col_f1, col_f2, col_f3 = st.columns(3)
            
            with col_f1:
                search1 = st.text_input("🔍 Buscar", "", key="search_enriched").strip().lower()
            
            with col_f2:
                has_phone = st.checkbox("📞 Com telefone", key="filter_phone")
            
            with col_f3:
                has_email = st.checkbox("✉️ Com email", key="filter_email")
            
            # Apply filters
            filtered_df = df.copy()
            
            if search1:
                mask = (
                    filtered_df["name"].str.lower().str.contains(search1) |
                    filtered_df["city"].fillna("").str.lower().str.contains(search1) |
                    filtered_df["region"].fillna("").str.lower().str.contains(search1)
                )
                filtered_df = filtered_df[mask]
            
            if has_phone:
                filtered_df = filtered_df[filtered_df["phone"].notna()]
            
            if has_email:
                filtered_df = filtered_df[filtered_df["email"].notna()]
            
            st.write(f"Mostrando {len(filtered_df)} de {len(df)} empresas")
            
            # Display table
            display_df = filtered_df[["name", "nif", "phone", "email", "website", "city", "region"]].copy()
            display_df.columns = ["Empresa", "NIF", "Telefone", "Email", "Website", "Cidade", "Região"]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400,
                column_config={
                    "Empresa": st.column_config.TextColumn("Empresa", width="large"),
                    "NIF": st.column_config.TextColumn("NIF", width="small"),
                    "Telefone": st.column_config.TextColumn("📞", width="small"),
                    "Email": st.column_config.LinkColumn("✉️", width="medium"),
                    "Website": st.column_config.LinkColumn("🌐", width="medium"),
                }
            )
            
            # Export
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar CSV",
                csv,
                f"empresas_enriquecidas_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
    
    # ==================== TAB 2: SEARCH RESULTS ====================
    with tab2:
        st.markdown("Empresas pesquisadas diretamente no [NIF.pt](https://www.nif.pt)")
        
        if not search_results:
            st.info("💡 Nenhum resultado de pesquisa encontrado. Execute `pt-nif-search` para pesquisar empresas.")
            st.code("pt-nif-search \"RESTAURANTE\"", language="bash")
        else:
            # Convert to dataframe
            search_list = []
            for company in search_results:
                row = {
                    "nif": company.get("nif"),
                    "name": company.get("name", "Unknown"),
                    "location": company.get("location", "N/A"),
                    "url": company.get("url", "")
                }
                search_list.append(row)
            
            df = pd.DataFrame(search_list)
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Total Pesquisadas", len(df))
            with col2:
                st.metric("Únicas", len(df))
            with col3:
                st.metric("Com Localização", len(df[df["location"] != "N/A"]))
            
            st.markdown("---")
            
            # Search filter
            search2 = st.text_input("🔍 Buscar", "", key="search_results").strip().lower()
            
            # Apply filters
            filtered_df = df.copy()
            
            if search2:
                mask = (
                    filtered_df["name"].str.lower().str.contains(search2) |
                    filtered_df["location"].str.lower().str.contains(search2)
                )
                filtered_df = filtered_df[mask]
            
            st.write(f"Mostrando {len(filtered_df)} de {len(df)} empresas")
            
            # Display table
            display_df = filtered_df[["name", "nif", "location"]].copy()
            display_df.columns = ["Empresa", "NIF", "Localização"]
            
            st.dataframe(
                display_df,
                use_container_width=True,
                height=400,
                column_config={
                    "Empresa": st.column_config.TextColumn("Empresa", width="large"),
                    "NIF": st.column_config.TextColumn("NIF", width="small"),
                    "Localização": st.column_config.TextColumn("📍", width="medium"),
                }
            )
            
            # Export
            csv = display_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Exportar CSV",
                csv,
                f"empresas_pesquisadas_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )


def main():
    # Page navigation
    st.sidebar.title("🇵🇹 Menu")
    page = st.sidebar.radio(
        "Selecione a página",
        ["📋 eInforma.pt", "📊 NIF.pt"],
        label_visibility="collapsed"
    )
    
    if page == "📋 eInforma.pt":
        show_einforma_page()
    elif page == "📊 NIF.pt":
        show_nif_page()


if __name__ == "__main__":
    main()
