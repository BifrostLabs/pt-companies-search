#!/usr/bin/env python3
"""
eInforma.pt - Novas Empresas
Uses database when available, falls back to JSON
Auto-refreshes every 30 seconds
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import database loader
from db_loader import get_einforma_dataframe, load_enriched_data, is_db_available

# Config
DATA_DIR = Path(__file__).parent.parent / "data"

# Auto-refresh every 30 seconds
REFRESH_INTERVAL = 30
AUTO_REFRESH_ENABLED = False

# Add auto-refresh via meta tag
if AUTO_REFRESH_ENABLED:
    st.markdown(f"""
        <meta http-equiv="refresh" content="{REFRESH_INTERVAL}">
        <style>
            .refresh-indicator {{
                position: fixed;
                top: 60px;
                right: 20px;
                background: #1A1D24;
                color: #FAFAFA;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                z-index: 999;
                border: 1px solid #333;
            }}
            .db-indicator {{
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 5px;
            }}
            .db-online {{ background: #00C851; }}
            .db-offline {{ background: #ff4444; }}
        </style>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
        <style>
            .refresh-indicator {{
                position: fixed;
                top: 60px;
                right: 20px;
                background: #1A1D24;
                color: #FAFAFA;
                padding: 8px 16px;
                border-radius: 20px;
                font-size: 12px;
                z-index: 999;
                border: 1px solid #333;
            }}
            .db-indicator {{
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-right: 5px;
            }}
            .db-online {{ background: #00C851; }}
            .db-offline {{ background: #ff4444; }}
        </style>
    """, unsafe_allow_html=True)

# Standard sector definitions
SECTORS = {
    "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL"],
    "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS"],
    "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO"],
    "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO", "MEDIÇÃO IMOBILIÁRIA"],
    "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA"],
}


def get_sector(name):
    """Classify company into sector"""
    if not name:
        return "Outro"
    name_upper = name.upper()
    for sector, keywords in SECTORS.items():
        if any(kw in name_upper for kw in keywords):
            return sector
    return "Outro"


@st.cache_data(ttl=3600)
def load_data():
    """Load data from database or JSON"""
    df = get_einforma_dataframe(use_historical=True)
    
    if df.empty:
        return None, None
    
    # Load enriched data
    enriched_data = load_enriched_data()
    
    return df, enriched_data


def merge_enriched_data(df, enriched_dict):
    """Merge enriched data into dataframe"""
    if not enriched_dict or df.empty:
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
    # Show refresh indicator
    db_status = "online" if is_db_available() else "offline"
    db_icon = "🗄️" if is_db_available() else "📁"
    refresh_text = f"🔄 Auto-refresh: {REFRESH_INTERVAL}s" if AUTO_REFRESH_ENABLED else "🔄 Refresh: Off"
    st.markdown(f"""
        <div class="refresh-indicator">
            <span class="db-indicator db-{db_status}"></span>
            {db_icon} {'PostgreSQL' if is_db_available() else 'JSON Mode'} | 
            {refresh_text}
        </div>
    """, unsafe_allow_html=True)
    
    # Center content
    _, col_main, _ = st.columns([0.05, 0.9, 0.05])
    
    with col_main:
        st.title("📋 eInforma.pt - Novas Empresas")
        st.markdown("Empresas recém-registradas em Portugal")
        
        # Show last update time
        st.caption(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
        
        # Add a refresh button to clear cache manually
        if st.button("🔄 Forçar Atualização de Dados"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Load data (from database or JSON)
        result = load_data()
        
        if not result or result[0].empty:
            st.error("Nenhum dado encontrado. Execute `pt-scrape` primeiro.")
            st.stop()
        
        df, enriched_data = result
        
        # Convert registration_date to date_obj for filtering
        if "registration_date" in df.columns:
            df["date_obj"] = pd.to_datetime(df["registration_date"], errors="coerce").dt.date
            df["date"] = df["registration_date"].apply(lambda x: x.strftime("%d-%m-%Y") if pd.notna(x) else "")
        else:
            df["date_obj"] = None
        
        # Merge enriched data
        if enriched_data:
            df = merge_enriched_data(df, enriched_data)
        
        # Render sidebar (simplified - no historical option for now)
        filters = render_compact_sidebar(df, enriched_data, has_historical=False)
        
        # Apply filters
        filtered_df = apply_filters(df, filters, enriched_data)
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total", len(df))
        with col2:
            st.metric("Filtradas", len(filtered_df))
        with col3:
            st.metric("Datas", df["date"].nunique() if "date" in df.columns else 0)
        with col4:
            if enriched_data:
                enriched_count = len([nif for nif in filtered_df["nif"] if nif in enriched_data])
                st.metric("Enriquecidas", enriched_count)
            else:
                st.metric("Modo", "PostgreSQL" if is_db_available() else "JSON")
        
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
