#!/usr/bin/env python3
"""
NIF.pt - Dados de Empresas
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

from pt_companies_search.core.database import (
    is_db_available, get_enriched_dataframe, get_search_dataframe, get_stats
)

# Standard sector definitions
SECTORS = {
    "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL"],
    "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS"],
    "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO"],
    "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO", "MEDIÇÃO IMOBILIÁRIA"],
    "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA"],
}

AUTO_REFRESH_ENABLED = False


def get_sector(name: str) -> str:
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
    """Load enriched and search data"""
    enriched_df = get_enriched_dataframe()
    search_df = get_search_dataframe()
    stats = get_stats()
    return enriched_df, search_df, stats


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
    
    st.title("📊 NIF.pt - Dados de Empresas")
    st.markdown("Empresas enriquecidas via API e pesquisadas na base NIF.pt")
    st.caption(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
    
    if st.button("🔄 Forçar Atualização de Dados"):
        st.cache_data.clear()
        st.rerun()
    
    # Tabs
    tab1, tab2 = st.tabs(["📦 Enriquecidos (API)", "🔍 Pesquisados (Scraped)"])
    
    enriched_df, search_df, stats = load_data()
    
    with tab1:
        st.subheader("Empresas Enriquecidas via NIF.pt API")
        
        if enriched_df.empty:
            st.info("Nenhuma empresa enriquecida ainda. Execute o enricher.")
        else:
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total", len(enriched_df))
            with col2:
                st.metric("Com Telefone", enriched_df["phone"].notna().sum())
            with col3:
                st.metric("Com Email", enriched_df["email"].notna().sum())
            with col4:
                st.metric("Com Website", enriched_df["website"].notna().sum())
            
            st.markdown("---")
            
            # Sector chart
            if "sector" in enriched_df.columns:
                sector_counts = enriched_df["sector"].value_counts().reset_index()
                sector_counts.columns = ["sector", "count"]
                fig = px.bar(sector_counts.head(10), x="sector", y="count", title="Top 10 Setores")
                st.plotly_chart(fig, use_container_width=True)
            
            # Filters
            col1, col2, col3 = st.columns(3)
            with col1:
                search = st.text_input("Buscar", "", placeholder="Nome ou NIF...").lower()
            with col2:
                has_phone = st.checkbox("Com telefone")
            with col3:
                has_email = st.checkbox("Com email")
            
            # Apply filters
            filtered_df = enriched_df.copy()
            if search:
                mask = (
                    filtered_df["name"].str.lower().str.contains(search, na=False) |
                    filtered_df["nif"].str.contains(search, na=False)
                )
                filtered_df = filtered_df[mask]
            if has_phone:
                filtered_df = filtered_df[filtered_df["phone"].notna()]
            if has_email:
                filtered_df = filtered_df[filtered_df["email"].notna()]
            
            st.metric("Resultados", len(filtered_df))
            
            # Display
            display_cols = ["nif", "name", "phone", "email", "website", "city", "sector"]
            available_cols = [c for c in display_cols if c in filtered_df.columns]
            st.dataframe(filtered_df[available_cols], use_container_width=True, height=500)
            
            # Export
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 Exportar CSV",
                csv,
                f"empresas_enriquecidas_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
    
    with tab2:
        st.subheader("Empresas Pesquisadas via NIF.pt")
        
        if search_df.empty:
            st.info("Nenhuma pesquisa realizada ainda. Execute o searcher.")
        else:
            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total", len(search_df))
            with col2:
                st.metric("Com Telefone", search_df["phone"].notna().sum() if "phone" in search_df.columns else 0)
            with col3:
                st.metric("Com Email", search_df["email"].notna().sum() if "email" in search_df.columns else 0)
            
            st.markdown("---")
            
            # Search filter
            search_query = st.text_input("Buscar", "", placeholder="Nome da empresa...", key="search_tab2").lower()
            
            filtered_df = search_df.copy()
            if search_query:
                filtered_df = filtered_df[filtered_df["name"].str.lower().str.contains(search_query, na=False)]
            
            st.metric("Resultados", len(filtered_df))
            
            # Display
            display_cols = ["nif", "name", "city", "region", "sector", "fetched_at"]
            available_cols = [c for c in display_cols if c in filtered_df.columns]
            st.dataframe(filtered_df[available_cols], use_container_width=True, height=500)
            
            # Export
            csv = filtered_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 Exportar CSV",
                csv,
                f"empresas_pesquisadas_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
    
    # Sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"📅 {datetime.now().strftime('%d/%m %H:%M')}")
    st.sidebar.caption("[NIF.pt](https://www.nif.pt)")


main()
