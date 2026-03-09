"""
Streamlit dashboard app entry point
"""

import streamlit as st
import pandas as pd
from datetime import datetime

from pt_companies_search.core.database import test_connection, get_contact_coverage, get_sector_stats, get_source_stats

st.set_page_config(
    page_title="PT Companies Search",
    page_icon="🇵🇹",
    layout="wide"
)

def main():
    st.title("🇵🇹 PT Companies Search")
    st.markdown("Track and enrich newly registered companies in Portugal.")
    
    db_available = test_connection()
    
    if not db_available:
        st.error("❌ Database connection failed. Please ensure PostgreSQL is running.")
        st.stop()
        
    st.success("✅ Database connected.")
    
    # Overview metrics
    stats = get_contact_coverage()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Companies", stats.get("total", 0))
    with col2:
        st.metric("With Phone", stats.get("with_phone", 0))
    with col3:
        st.metric("With Email", stats.get("with_email", 0))
    with col4:
        st.metric("With Website", stats.get("with_website", 0))
        
    st.divider()
    
    # Sector Stats
    st.subheader("🏢 Companies by Sector")
    sector_stats = get_sector_stats()
    if sector_stats:
        df_sector = pd.DataFrame(sector_stats)
        st.bar_chart(df_sector.set_index("sector")["total"])
        
    # Source Stats
    st.subheader("📂 Companies by Source")
    source_stats = get_source_stats()
    if source_stats:
        df_source = pd.DataFrame(source_stats)
        st.table(df_source)

if __name__ == "__main__":
    main()
