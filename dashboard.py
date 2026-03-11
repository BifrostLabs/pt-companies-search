#!/usr/bin/env python3
"""
Portugal New Companies - Main Dashboard
"""

import streamlit as st
from datetime import datetime
import plotly.express as px
import pandas as pd

# Check connection and imports
try:
    from pt_companies_search.core.database import (
        is_db_available, get_stats, get_sector_stats, get_region_stats
    )
    from pt_companies_search.dashboard.components.styles import apply_custom_styles, render_header, render_footer
    from pt_companies_search.dashboard.components.cards import metric_card, section_header
except ImportError as e:
    st.error(f"Import Error: {e}. Check directory structure and PYTHONPATH.")
    st.stop()

# Config
st.set_page_config(
    page_title="Portugal New Companies",
    page_icon="🇵🇹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global custom styles
apply_custom_styles()

def main_home():
    render_header("Portugal New Companies", "Company tracking and enrichment system overview.")
    
    # Statistics
    stats = get_stats()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Scraped", f"{stats['einforma_total']:,}", icon="📋", subtitle="From eInforma.pt")
    with col2:
        metric_card("Enriched Total", f"{stats['enriched_total']:,}", icon="✨", subtitle="Via NIF.pt API")
    with col3:
        metric_card("Contact Coverage", f"{stats['enriched_with_contact']:,}", icon="📞", subtitle="Phone/Email found")
    with col4:
        metric_card("Search Results", f"{stats['search_total']:,}", icon="🔍", subtitle="NIF.pt Search")

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([0.6, 0.4])
    
    with col_left:
        section_header("Sector Distribution", icon="🏢")
        sector_stats = get_sector_stats()
        if sector_stats:
            df_sector = pd.DataFrame(sector_stats).head(10)
            fig = px.bar(
                df_sector, 
                x="count", 
                y="sector", 
                orientation='h',
                title="Top 10 Sectors",
                labels={"count": "Companies", "sector": "Sector"},
                color="count",
                color_continuous_scale="Viridis"
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#FAFAFA',
                margin=dict(l=0, r=0, t=30, b=0),
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No sector data available yet.")

    with col_right:
        section_header("Regional Data", icon="📍")
        region_stats = get_region_stats()
        if region_stats:
            df_region = pd.DataFrame(region_stats).head(10)
            fig = px.pie(
                df_region, 
                values="count", 
                names="region", 
                hole=0.4,
                title="Top Regions"
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                font_color='#FAFAFA',
                margin=dict(l=0, r=0, t=30, b=0),
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No regional data available yet.")

    section_header("Quick Actions", icon="⚡")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 📋 eInforma.pt
        Explore daily registered companies.
        """)
        if st.button("Open eInforma Explorer", use_container_width=True):
            st.switch_page("pt_companies_search/dashboard/pages/einforma.py")
            
    with col2:
        st.markdown("""
        ### 📊 NIF.pt
        View enriched contact details.
        """)
        if st.button("Open NIF.pt Explorer", use_container_width=True):
            st.switch_page("pt_companies_search/dashboard/pages/nif.py")
            
    with col3:
        st.markdown("""
        ### 🔄 System
        Maintenance and configuration.
        """)
        if st.button("Clear Application Cache", use_container_width=True):
            st.cache_data.clear()
            st.toast("Cache cleared!")

    render_footer()

# Sidebar
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 25px; background: #1A1D24; padding: 20px; border-radius: 12px; border: 1px solid #30363D;">
            <h1 style="font-size: 40px; margin-bottom: 0;">🇵🇹</h1>
            <h3 style="margin-top: 10px; font-weight: 700;">PT Companies</h3>
            <p style="color: #8B949E; font-size: 0.8rem;">BifrostLabs Tracker</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🏠 Navigation")
    # Streamlit automatically handles multipage if we use st.navigation
    # But since we are inside a package, we need to be careful with paths

pg = st.navigation([
    st.Page(main_home, title="Home", icon="🏠", default=True),
    st.Page("pt_companies_search/dashboard/pages/einforma.py", title="eInforma.pt", icon="📋"),
    st.Page("pt_companies_search/dashboard/pages/nif.py", title="NIF.pt", icon="📊"),
])

pg.run()
