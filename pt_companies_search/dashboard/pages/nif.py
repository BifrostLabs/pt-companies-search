#!/usr/bin/env python3
"""
NIF.pt - Dados de Empresas (Refactored UI/UX with Polars)
"""

import streamlit as st
import polars as pl
from datetime import datetime
import plotly.express as px

# Check connection and imports
try:
    from pt_companies_search.core.database import (
        is_db_available, get_enriched_dataframe, get_search_dataframe, get_stats
    )
    from pt_companies_search.dashboard.components.styles import apply_custom_styles, render_header, render_footer
    from pt_companies_search.dashboard.components.cards import metric_card, section_header
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
            <div style="text-align: center; margin-bottom: 25px; background: #1A1D24; padding: 20px; border-radius: 12px; border: 1px solid #30363D;">
                <h1 style="font-size: 40px; margin-bottom: 0;">📊</h1>
                <h3 style="margin-top: 10px; font-weight: 700;">NIF.pt</h3>
                <p style="color: #8B949E; font-size: 0.8rem;">Enrichment Explorer</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔍 Filters")
        search_query = st.text_input("Name/NIF Search", "", placeholder="Search...").lower()
        
        has_phone = st.checkbox("📞 With phone number")
        has_email = st.checkbox("✉️ With email address")
        has_website = st.checkbox("🌐 With website")
        
        st.markdown("---")
        
        st.markdown("### ⚡ Actions")
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
    filtered_df = df
    if filters["search"]:
        s = filters["search"]
        filtered_df = filtered_df.filter(
            (pl.col("name").str.to_lowercase().str.contains(s)) |
            (pl.col("nif").str.to_lowercase().str.contains(s))
        )
    
    if filters["phone"] and "phone" in filtered_df.columns:
        filtered_df = filtered_df.filter(pl.col("phone").is_not_null())
    if filters["email"] and "email" in filtered_df.columns:
        filtered_df = filtered_df.filter(pl.col("email").is_not_null())
    if filters["website"] and "website" in filtered_df.columns:
        filtered_df = filtered_df.filter(pl.col("website").is_not_null())
        
    return filtered_df

def main():
    # Header area
    render_header("NIF.pt - Dados de Empresas", "Companies enriched via API and discovered through search.")

    # Load data
    enriched_df, search_df, stats = load_data()
    
    # Render sidebar and get filters
    filters = render_sidebar()
    
    # Tabs for different data sources
    tab1, tab2 = st.tabs(["📦 Enriched Companies (API)", "🔍 Search Results (Scraped)"])
    
    with tab1:
        if enriched_df.is_empty():
            st.info("No companies enriched yet. Run the enricher script to populate this view.")
        else:
            # Apply filters
            filtered_enriched = apply_filters(enriched_df, filters)
            
            # Metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                metric_card("Total Enriched", f"{len(enriched_df):,}", icon="📦")
            with col2:
                with_phone = enriched_df.filter(pl.col("phone").is_not_null()).height
                phone_pct = (with_phone / len(enriched_df)) * 100 if not enriched_df.is_empty() else 0
                metric_card("Phone Coverage", f"{with_phone:,}", subtitle=f"{phone_pct:.1f}%", icon="📞")
            with col3:
                with_email = enriched_df.filter(pl.col("email").is_not_null()).height
                email_pct = (with_email / len(enriched_df)) * 100 if not enriched_df.is_empty() else 0
                metric_card("Email Coverage", f"{with_email:,}", subtitle=f"{email_pct:.1f}%", icon="✉️")
            with col4:
                metric_card("Results Found", f"{len(filtered_enriched):,}", icon="🔍")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Distribution Chart
            if "sector" in enriched_df.columns:
                sector_counts = enriched_df.select("sector").drop_nulls().group_by("sector").count().sort("count", descending=True).head(10).to_pandas()
                sector_counts.columns = ["Sector", "Count"]
                fig = px.pie(sector_counts, values="Count", names="Sector", hole=0.4, title="Top 10 Enriched Sectors")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='#FAFAFA', margin=dict(l=0, r=0, t=40, b=0), height=350)
                st.plotly_chart(fig, use_container_width=True)
            
            # Dataframe view
            section_header("Data Explorer", icon="📦")
            
            # Prepare data for display
            display_enriched = filtered_enriched.to_pandas()
            if "nif" in display_enriched.columns:
                display_enriched["nif_link"] = display_enriched["nif"].apply(lambda x: f"https://www.nif.pt/{x}/")

            st.dataframe(
                display_enriched,
                column_config={
                    "nif_link": st.column_config.LinkColumn("NIF", display_text=r"https://www.nif.pt/(.+)/"),
                    "name": "Company Name",
                    "email": st.column_config.LinkColumn("Email"),
                    "website": st.column_config.LinkColumn("Website"),
                    "enriched_at": st.column_config.DatetimeColumn("Enriched At", format="DD/MM/YYYY HH:mm"),
                },
                column_order=["nif_link", "name", "email", "website", "city", "enriched_at"],
                hide_index=True,
                use_container_width=True,
                height=500
            )
            
            # Export
            csv = filtered_enriched.to_pandas().to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 Export Enriched Results CSV",
                csv,
                f"enriched_companies_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )
            
    with tab2:
        if search_df.is_empty():
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
                city_count = search_df.select("city").n_unique() if "city" in search_df.columns else 0
                metric_card("Unique Cities", f"{city_count}", icon="📍")
                
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Dataframe view
            section_header("Search Explorer", icon="🔍")
            
            # Prepare data for display
            display_search = filtered_search.to_pandas()
            if "nif" in display_search.columns:
                display_search["nif_link"] = display_search["nif"].apply(lambda x: f"https://www.nif.pt/{x}/")

            st.dataframe(
                display_search,
                column_config={
                    "nif_link": st.column_config.LinkColumn("NIF", display_text=r"https://www.nif.pt/(.+)/"),
                    "name": "Company Name",
                    "fetched_at": st.column_config.DatetimeColumn("Discovered At", format="DD/MM/YYYY HH:mm"),
                },
                column_order=["nif_link", "name", "city", "fetched_at"],
                hide_index=True,
                use_container_width=True,
                height=500
            )
            
            # Export
            csv = filtered_search.to_pandas().to_csv(index=False).encode("utf-8")
            st.download_button(
                "📄 Export Search Results CSV",
                csv,
                f"search_results_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )

    render_footer()

if __name__ == "__main__":
    main()
