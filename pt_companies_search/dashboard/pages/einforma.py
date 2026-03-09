#!/usr/bin/env python3
"""
eInforma.pt - Novas Empresas
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from pt_companies_search.core.database import (
    is_db_available, get_einforma_dataframe, load_enriched_data
)

# Config
AUTO_REFRESH_ENABLED = False

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
    """Load data from database"""
    df = get_einforma_dataframe(use_historical=True)
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
                    "cae", "activity_description", "status", "region", "county", "parish"]:
            row[f"enriched_{key}"] = enriched.get(key)
        enriched_rows.append(row)
    
    if not enriched_rows:
        return df
    
    enriched_df = pd.DataFrame(enriched_rows)
    return df.merge(enriched_df, on="nif", how="left")


def render_sidebar(df, enriched_data):
    """Render sidebar filters"""
    st.sidebar.markdown("**🔍 Buscar**")
    search = st.sidebar.text_input("Buscar", "", placeholder="Nome da empresa...", label_visibility="collapsed").strip().lower()
    
    st.sidebar.markdown("**📅 Data**")
    if "registration_date" in df.columns and not df["registration_date"].isna().all():
        min_date = df["registration_date"].min()
        max_date = df["registration_date"].max()
        date_range = st.sidebar.date_input("Período", value=(min_date, max_date), label_visibility="collapsed")
    else:
        date_range = None
    
    show_enriched_only = False
    if enriched_data:
        st.sidebar.markdown("**📊 Dados**")
        enriched_count = len([nif for nif in df["nif"] if nif in enriched_data])
        show_enriched_only = st.sidebar.checkbox(f"Apenas enriquecidas ({enriched_count})")
    
    st.sidebar.markdown("**🏢 Setor**")
    selected_sectors = st.sidebar.multiselect("Setor", list(SECTORS.keys()), label_visibility="collapsed", placeholder="Todos os setores")
    
    return {
        "search": search,
        "date_range": date_range,
        "show_enriched_only": show_enriched_only,
        "sectors": selected_sectors,
    }


def apply_filters(df, filters, enriched_data):
    """Apply filters to dataframe"""
    filtered_df = df.copy()
    
    if filters["date_range"] and isinstance(filters["date_range"], tuple) and len(filters["date_range"]) == 2:
        start_date, end_date = filters["date_range"]
        if "registration_date" in filtered_df.columns:
            filtered_df = filtered_df[
                (filtered_df["registration_date"] >= pd.Timestamp(start_date)) & 
                (filtered_df["registration_date"] <= pd.Timestamp(end_date))
            ]
    
    if filters["search"]:
        filtered_df = filtered_df[filtered_df["name"].str.lower().str.contains(filters["search"], na=False)]
    
    if filters["sectors"]:
        all_keywords = []
        for sector in filters["sectors"]:
            all_keywords.extend(SECTORS.get(sector, []))
        if all_keywords:
            mask = filtered_df["name"].str.upper().apply(
                lambda x: any(kw in str(x).upper() for kw in all_keywords)
            )
            filtered_df = filtered_df[mask]
    
    if filters["show_enriched_only"] and enriched_data:
        enriched_nifs = set(enriched_data.keys())
        filtered_df = filtered_df[filtered_df["nif"].isin(enriched_nifs)]
    
    return filtered_df


def main():
    # Status indicator
    db_status = "online" if is_db_available() else "offline"
    db_icon = "🗄️" if is_db_available() else "📁"
    st.markdown(f"""
        <div style="position: fixed; top: 60px; right: 20px; background: #1A1D24; color: #FAFAFA; padding: 8px 16px; border-radius: 20px; font-size: 12px; z-index: 999; border: 1px solid #333;">
            <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 5px; background: {'#00C851' if is_db_available() else '#ff4444'};"></span>
            {db_icon} {'PostgreSQL' if is_db_available() else 'JSON Mode'} | 🔄 Refresh: Off
        </div>
    """, unsafe_allow_html=True)
    
    st.title("📋 eInforma.pt - Novas Empresas")
    st.markdown("Empresas recém-registradas em Portugal")
    st.caption(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
    
    if st.button("🔄 Forçar Atualização de Dados"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Load data
    df, enriched_data = load_data()
    
    if df.empty:
        st.error("Nenhum dado encontrado. Execute o scraper primeiro.")
        st.stop()
    
    # Convert registration_date for display
    if "registration_date" in df.columns:
        df["date_obj"] = pd.to_datetime(df["registration_date"], errors="coerce").dt.date
        df["date"] = df["registration_date"].apply(lambda x: x.strftime("%d-%m-%Y") if pd.notna(x) else "")
    else:
        df["date_obj"] = None
        df["date"] = ""
    
    # Merge enriched data
    if enriched_data:
        df = merge_enriched_data(df, enriched_data)
    
    # Render sidebar
    filters = render_sidebar(df, enriched_data)
    
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
        
        st.dataframe(display_df, use_container_width=True, height=600)
    else:
        for _, row in filtered_df.head(100).iterrows():
            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.markdown(f"**{row['name']}**")
                with col2:
                    st.markdown(f"📅 {row['date']}")
                with col3:
                    url = row.get('source_url', '')
                    if url:
                        st.markdown(f"[🔗 {row['nif']}]({url})")
                    else:
                        st.markdown(f"🔗 {row['nif']}")
                
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
    
    # Sidebar export
    csv = filtered_df.to_csv(index=False).encode("utf-8")
    st.sidebar.download_button(
        "📄 CSV",
        csv,
        f"empresas_einforma_{datetime.now().strftime('%Y%m%d')}.csv",
        "text/csv"
    )
    
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"📅 {datetime.now().strftime('%d/%m %H:%M')}")
    st.sidebar.caption("[eInforma.pt](https://www.einforma.pt)")


main()
