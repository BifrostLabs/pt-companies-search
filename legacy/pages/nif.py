#!/usr/bin/env python3
"""
NIF.pt - Dados de Empresas
Uses database when available, falls back to JSON
Auto-refreshes every 30 seconds
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import plotly.express as px

# Import database loader
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_loader import (
    get_enriched_dataframe,
    get_search_dataframe,
    get_stats,
    is_db_available,
    SECTORS,
)

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

# Config
st.set_page_config(
    page_title="NIF.pt - Dados",
    page_icon="📊",
    layout="wide"
)


def render_sidebar(df, data_type="enriched"):
    """Render sidebar filters"""
    
    # Search
    search = st.sidebar.text_input(
        "🔍 Buscar", "", 
        placeholder="Nome, cidade...",
        key=f"search_{data_type}"
    ).strip().lower()
    
    # Contact filters (only for enriched)
    has_phone = has_email = has_website = False
    if data_type == "enriched":
        st.sidebar.markdown("**📞 Contacto**")
        col1, col2, col3 = st.sidebar.columns(3)
        with col1:
            has_phone = st.checkbox("📞", key=f"phone_{data_type}", help="Telefone")
        with col2:
            has_email = st.checkbox("✉️", key=f"email_{data_type}", help="Email")
        with col3:
            has_website = st.checkbox("🌐", key=f"web_{data_type}", help="Website")
    
    # Sector filter
    st.sidebar.markdown("**🏢 Setor**")
    available_sectors = [s for s in SECTORS.keys() if not df.empty and len(df[df["sector"] == s]) > 0]
    selected_sectors = st.sidebar.multiselect(
        "Setor",
        available_sectors,
        label_visibility="collapsed",
        placeholder="Todos",
        key=f"sectors_{data_type}"
    )
    
    # Location filter
    selected_regions = []
    selected_cities = []
    
    if data_type == "enriched" and not df.empty:
        st.sidebar.markdown("**🗺️ Região**")
        regions = sorted(df["region"].dropna().unique().tolist())
        selected_regions = st.sidebar.multiselect(
            "Região",
            regions[:15],
            label_visibility="collapsed",
            placeholder="Todas",
            key=f"regions_{data_type}"
        )
    elif data_type == "search" and not df.empty:
        st.sidebar.markdown("**🏙️ Cidade**")
        cities = sorted(df[df["city"] != "N/A"]["city"].dropna().unique().tolist())
        selected_cities = st.sidebar.multiselect(
            "Cidade",
            cities[:15],
            label_visibility="collapsed",
            placeholder="Todas",
            key=f"cities_{data_type}"
        )
    
    return {
        "search": search,
        "has_phone": has_phone,
        "has_email": has_email,
        "has_website": has_website,
        "sectors": selected_sectors,
        "regions": selected_regions,
        "cities": selected_cities
    }


def apply_filters(df, filters, data_type="enriched"):
    """Apply filters to dataframe"""
    if df.empty:
        return df
    
    filtered_df = df.copy()
    
    if filters["search"]:
        search_cols = ["name"]
        if "city" in filtered_df.columns:
            search_cols.append("city")
        if "region" in filtered_df.columns:
            search_cols.append("region")
        if "location" in filtered_df.columns:
            search_cols.append("location")
        
        mask = filtered_df[search_cols].fillna("").apply(
            lambda row: filters["search"] in " ".join(row.astype(str)).lower(),
            axis=1
        )
        filtered_df = filtered_df[mask]
    
    if data_type == "enriched":
        if filters["has_phone"] and "phone" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["phone"].notna()]
        if filters["has_email"] and "email" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["email"].notna()]
        if filters["has_website"] and "website" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["website"].notna()]
    
    if filters["sectors"]:
        filtered_df = filtered_df[filtered_df["sector"].isin(filters["sectors"])]
    
    if data_type == "enriched" and filters["regions"] and "region" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["region"].isin(filters["regions"])]
    
    if data_type == "search" and filters.get("cities") and "city" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["city"].isin(filters["cities"])]
    
    return filtered_df


def render_enriched_tab(df, filters):
    """Render enriched data tab"""
    st.markdown("### Dados completos de contacto via API")
    
    if df.empty:
        st.info("💡 Nenhum dado enriquecido encontrado.")
        st.code("""pt-nif-enrich --source historical""", language="bash")
        return pd.DataFrame()
    
    filtered_df = apply_filters(df, filters, "enriched")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total", len(df))
    with col2:
        st.metric("📞 Telefone", len(df[df["phone"].notna()]) if "phone" in df.columns else 0)
    with col3:
        st.metric("✉️ Email", len(df[df["email"].notna()]) if "email" in df.columns else 0)
    with col4:
        st.metric("🌐 Website", len(df[df["website"].notna()]) if "website" in df.columns else 0)
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 Por Setor")
        sector_counts = filtered_df["sector"].value_counts()
        if len(sector_counts) > 0:
            fig = px.bar(
                x=sector_counts.values, y=sector_counts.index,
                orientation='h', color=sector_counts.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📞 Contacto")
        if "phone" in filtered_df.columns:
            contact_data = {
                'Tipo': ['Telefone', 'Email', 'Website', 'Sem contacto'],
                'Qtd': [
                    len(filtered_df[filtered_df["phone"].notna()]),
                    len(filtered_df[filtered_df["email"].notna()]) if "email" in filtered_df.columns else 0,
                    len(filtered_df[filtered_df["website"].notna()]) if "website" in filtered_df.columns else 0,
                    len(filtered_df[filtered_df["phone"].isna() & filtered_df.get("email", pd.Series()).isna() & filtered_df.get("website", pd.Series()).isna()])
                ]
            }
            fig = px.pie(contact_data, values='Qtd', names='Tipo',
                        color_discrete_sequence=px.colors.sequential.Blues_r)
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Table
    st.subheader("📋 Dados")
    st.write(f"Mostrando **{len(filtered_df)}** de **{len(df)}** empresas")
    
    display_cols = ["name", "nif"]
    if "phone" in filtered_df.columns:
        display_cols.append("phone")
    if "email" in filtered_df.columns:
        display_cols.append("email")
    if "website" in filtered_df.columns:
        display_cols.append("website")
    if "city" in filtered_df.columns:
        display_cols.append("city")
    if "region" in filtered_df.columns:
        display_cols.append("region")
    display_cols.append("sector")
    
    display_df = filtered_df[display_cols].copy()
    display_df.columns = ["Empresa", "NIF", "Telefone", "Email", "Website", "Cidade", "Região", "Setor"][:len(display_cols)]
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    return display_df


def render_search_tab(df, filters):
    """Render search results tab"""
    st.markdown("### Empresas encontradas via pesquisa direta")
    
    if df.empty:
        st.info("💡 Nenhum resultado de pesquisa encontrado.")
        st.code("""pt-nif-search "RESTAURANTE" """, language="bash")
        return pd.DataFrame()
    
    filtered_df = apply_filters(df, filters, "search")
    
    # Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", len(df))
    with col2:
        st.metric("Filtradas", len(filtered_df))
    with col3:
        st.metric("Com Localização", len(df[df["location"] != "N/A"]) if "location" in df.columns else len(df))
    
    st.markdown("---")
    
    # Charts
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🏢 Por Setor")
        sector_counts = filtered_df["sector"].value_counts()
        if len(sector_counts) > 0:
            fig = px.bar(
                x=sector_counts.values, y=sector_counts.index,
                orientation='h', color=sector_counts.values,
                color_continuous_scale='Oranges'
            )
            fig.update_layout(height=300, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("🏙️ Top Cidades")
        if "city" in filtered_df.columns:
            city_counts = filtered_df[filtered_df["city"] != "N/A"]["city"].value_counts().head(10)
            if len(city_counts) > 0:
                fig = px.bar(
                    x=city_counts.values, y=city_counts.index,
                    orientation='h', color=city_counts.values,
                    color_continuous_scale='Reds'
                )
                fig.update_layout(height=300, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Table
    st.subheader("📋 Dados")
    st.write(f"Mostrando **{len(filtered_df)}** de **{len(df)}** empresas")
    
    display_cols = ["name", "nif"]
    if "location" in filtered_df.columns:
        display_cols.append("location")
    if "city" in filtered_df.columns:
        display_cols.append("city")
    display_cols.append("sector")
    
    display_df = filtered_df[display_cols].copy()
    display_df.columns = ["Empresa", "NIF", "Localização", "Cidade", "Setor"][:len(display_cols)]
    
    st.dataframe(display_df, use_container_width=True, height=400)
    
    st.info("💡 **Dica**: Use `pt-enrich-search` para enriquecer estas empresas")
    
    return display_df


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
        st.title("📊 NIF.pt - Dados de Empresas")
        st.markdown("Empresas pesquisadas e enriquecidas via [NIF.pt](https://www.nif.pt)")
        
        # Show last update time
        st.caption(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
        
        # Add a refresh button to clear cache manually
        if st.button("🔄 Forçar Atualização de Dados"):
            st.cache_data.clear()
            st.rerun()
        
        # Database status
        if is_db_available():
            st.sidebar.success("🗄️ PostgreSQL")
        else:
            st.sidebar.info("📁 JSON")
        
        # Load data (auto-refreshes with DB)
        df_enriched = get_enriched_dataframe()
        df_search = get_search_dataframe()
        
        # Tabs
        tab1, tab2 = st.tabs(["📊 Enriquecidos", "🔍 Pesquisados"])
        
        with tab1:
            filters_enriched = render_sidebar(df_enriched, "enriched")
            display_df_enriched = render_enriched_tab(df_enriched, filters_enriched)
        
        with tab2:
            filters_search = render_sidebar(df_search, "search")
            display_df_search = render_search_tab(df_search, filters_search)
    
    # Export section
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📥 Exportar**")
    
    if not display_df_enriched.empty:
        csv = display_df_enriched.to_csv(index=False).encode("utf-8")
        st.sidebar.download_button(
            "📄 CSV Enriquecidos",
            csv,
            f"enriquecidos_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    if not display_df_search.empty:
        csv = display_df_search.to_csv(index=False).encode("utf-8")
        st.sidebar.download_button(
            "📄 CSV Pesquisados",
            csv,
            f"pesquisados_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
    
    # Refresh
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 Atualizar", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    
    st.sidebar.caption(f"📅 {datetime.now().strftime('%d/%m %H:%M')}")


main()
