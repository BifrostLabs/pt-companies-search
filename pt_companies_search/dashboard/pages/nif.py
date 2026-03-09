#!/usr/bin/env python3
"""
NIF.pt - Dados de Empresas (Refactored UI/UX)
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px

# Check connection and imports
try:
    from pt_companies_search.core.database import (
        is_db_available, get_enriched_dataframe, get_search_dataframe, get_stats
    )
    from pt_companies_search.dashboard.components.styles import apply_custom_styles
    from pt_companies_search.dashboard.components.cards import metric_card
except ImportError as e:
    st.error(f"Import Error: {e}. Check directory structure and PYTHONPATH.")
    st.stop()

# Config
st.set_page_config(
    page_title="NIF.pt - PT Companies",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global custom styles
apply_custom_styles()

@st.cache_data(ttl=3600)
def load_data():
    """Load enriched and search data"""
    enriched_df = get_enriched_dataframe()
    search_df = get_search_dataframe()
    stats = get_stats()
    return enriched_df, search_df, stats

def render_sidebar():
    """Render sidebar navigation/filters"""
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <h1 style="font-size: 32px; margin-bottom: 0;">📊</h1>
                <h3 style="margin-top: 5px;">NIF.pt</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        st.markdown("**🔍 Filters**")
        search_query = st.text_input("Name/NIF Search", "", placeholder="Search...").lower()
        
        has_phone = st.checkbox("📞 With phone number")
        has_email = st.checkbox("✉️ With email address")
        has_website = st.checkbox("🌐 With website")
        
        st.markdown("---")
        
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        st.caption(f"Last heartbeat: {datetime.now().strftime('%H:%M:%S')}")
        st.caption("[NIF.pt](https://www.nif.pt)")

    return {
        "search": search_query,
        "phone": has_phone,
        "email": has_email,
        "website": has_website
    }

def apply_filters(df, filters):
    """Apply generic filters to dataframe"""
    filtered_df = df.copy()
    if filters["search"]:
        mask = (
            filtered_df["name"].str.lower().str.contains(filters["search"], na=False) |
            filtered_df["nif"].str.lower().str.contains(filters["search"], na=False)
        )
        filtered_df = filtered_df[mask]
    
    if filters["phone"] and "phone" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["phone"].notna()]
    if filters["email"] and "email" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["email"].notna()]
    if filters["website"] and "website" in filtered_df.columns:
        filtered_df = filtered_df[filtered_df["website"].notna()]
        
    return filtered_df

def main():
    # Header area
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("📊 NIF.pt - Dados de Empresas")
        st.markdown("<p style='color: #8B949E; margin-top: -10px;'>Companies enriched via API and discovered through search.</p>", unsafe_allow_html=True)
    with col_h2:
        db_icon = "🗄️" if is_db_available() else "📁"
        st.markdown(f"""
            <div style="text-align: right; margin-top: 15px;">
                <span class="status-pill {'status-online' if is_db_available() else 'status-offline'}">
                    {db_icon} {'PostgreSQL Connected' if is_db_available() else 'Offline Mode'}
                </span>
            </div>
        """, unsafe_allow_html=True)

    # Load data
    enriched_df, search_df, stats = load_data()
    
    # Render sidebar and get filters
    filters = render_sidebar()
    
    # Tabs for different data sources
    tab1, tab2 = st.tabs(["📦 Enriched Companies (API)", "🔍 Search Results (Scraped)"])
    
    with tab1:
        if enriched_df.empty:
            st.info("No companies enriched yet. Run the enricher script to populate this view.")
        else:
            # Apply filters
            filtered_enriched = apply_filters(enriched_df, filters)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                metric_card("Total Enriched", f"{len(enriched_df):,}", icon="📦")
            with col2:
                phone_pct = (enriched_df["phone"].notna().sum() / len(enriched_df)) * 100
                metric_card("Phone Coverage", f"{enriched_df['phone'].notna().sum():,}", subtitle=f"{phone_pct:.1f}%", icon="📞")
            with col3:
                email_pct = (enriched_df["email"].notna().sum() / len(enriched_df)) * 100
                metric_card("Email Coverage", f"{enriched_df['email'].notna().sum():,}", subtitle=f"{email_pct:.1f}%", icon="✉️")
            with col4:
                metric_card("Results Found", f"{len(filtered_enriched):,}", icon="🔍")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Distribution Chart
            if "sector" in enriched_df.columns:
                sector_counts = enriched_df["sector"].value_counts().reset_index().head(10)
                sector_counts.columns = ["Sector", "Count"]
                fig = px.pie(sector_counts, values="Count", names="Sector", hole=0.4, title="Top 10 Enriched Sectors")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#FAFAFA', margin=dict(l=0, r=0, t=40, b=0), height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            # Dataframe view
            st.subheader("Data Explorer")
            st.dataframe(
                filtered_enriched,
                column_config={
                    "nif": "NIF",
                    "name": "Company Name",
                    "email": st.column_config.LinkColumn("Email"),
                    "website": st.column_config.LinkColumn("Website"),
                    "enriched_at": st.column_config.DatetimeColumn("Enriched At", format="DD/MM/YYYY HH:mm"),
                },
                hide_index=True,
                use_container_width=True,
                height=500
            )
            
            # Export
            csv = filtered_enriched.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 Export Enriched Results CSV",
                csv,
                f"enriched_companies_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )
            
    with tab2:
        if search_df.empty:
            st.info("No search results found yet. Run the searcher script to populate this view.")
        else:
            # Apply filters
            filtered_search = apply_filters(search_df, filters)
            
            # Metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                metric_card("Total Discovered", f"{len(search_df):,}", icon="🔍")
            with col2:
                metric_card("Total in Results", f"{len(filtered_search):,}", icon="📊")
            with col3:
                metric_card("Unique Cities", f"{search_df['city'].nunique() if 'city' in search_df.columns else 0}", icon="📍")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Dataframe view
            st.subheader("Data Explorer")
            st.dataframe(
                filtered_search,
                column_config={
                    "nif": "NIF",
                    "name": "Company Name",
                    "fetched_at": st.column_config.DatetimeColumn("Discovered At", format="DD/MM/YYYY HH:mm"),
                },
                hide_index=True,
                use_container_width=True,
                height=500
            )
            
            # Export
            csv = filtered_search.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 Export Search Results CSV",
                csv,
                f"search_results_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )

if __name__ == "__main__":
    main()
