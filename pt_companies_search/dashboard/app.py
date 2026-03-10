"""
Streamlit dashboard app entry point - Refactored UI/UX with Polars and Authentication
"""

import os
import streamlit as st
import polars as pl
from datetime import datetime
import plotly.express as px

# --- Streamlit Page Config (MUST BE FIRST) ---
st.set_page_config(
    page_title="PT Companies Dashboard",
    page_icon="🇵🇹",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Check connection and imports (AFTER page config)
try:
    from pt_companies_search.core.database import (
        test_connection, get_contact_coverage, get_sector_stats,
        get_source_stats, get_region_stats, is_db_available
    )
    from pt_companies_search.dashboard.components.styles import apply_custom_styles
    from pt_companies_search.dashboard.components.cards import metric_card, timeline_event
except ImportError as e:
    st.error(f"Import Error: {e}. Check directory structure and PYTHONPATH.")
    st.stop()

# Apply global custom styles (AFTER page config)
apply_custom_styles()

def login_ui():
    """
    Render a modern login UI for token authentication.
    """
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="font-size: 48px; margin-bottom: 0;">🇵🇹</h1>
                <h2 style="margin-top: 10px;">Welcome Back</h2>
                <p style="color: #8B949E;">Access the PT Companies Dashboard</p>
            </div>
        """, unsafe_allow_html=True)

        # Get token from environment
        admin_token = os.environ.get("ADMIN_TOKEN", "changeme")

        with st.form("login_form"):
            token_input = st.text_input("Access Token", type="password", placeholder="Enter your token...")
            submit = st.form_submit_button("Sign In", use_container_width=True)

            if submit:
                if token_input == admin_token:
                    st.session_state["authenticated"] = True
                    st.success("Authenticated successfully!")
                    st.rerun()
                else:
                    st.error("Invalid token. Please try again.")

def main_dashboard():
    """
    Main dashboard view with metrics and charts.
    """
    # Header area
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("🇵🇹 Dashboard Overview")
        st.markdown("<p style='color: #8B949E; margin-top: -10px;'>Track and analyze Portuguese company registrations in real-time.</p>", unsafe_allow_html=True)
    with col_h2:
        st.markdown("<div style='text-align: right; margin-top: 25px;'>", unsafe_allow_html=True)
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.toast("Refreshing data...", icon="🔄")
        st.markdown("</div>", unsafe_allow_html=True)

    db_available = test_connection()

    if not db_available:
        st.error("❌ Database connection failed. Please ensure PostgreSQL is running.")
        st.stop()

    # Stats row
    stats = get_contact_coverage()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Companies", f"{stats.get('total', 0):,}", icon="🏢")
    with col2:
        phone_pct = (stats.get("with_phone", 0) / stats.get("total", 1)) * 100
        metric_card("With Phone", f"{stats.get('with_phone', 0):,}", subtitle=f"{phone_pct:.1f}% coverage", icon="📞")
    with col3:
        email_pct = (stats.get('with_email', 0) / stats.get("total", 1)) * 100
        metric_card("With Email", f"{stats.get('with_email', 0):,}", subtitle=f"{email_pct:.1f}% coverage", icon="✉️")
    with col4:
        metric_card("Database Status", "Healthy", subtitle="PostgreSQL Online", icon="🗄️")

    st.markdown("<br>", unsafe_allow_html=True)

    # Insights Row
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🏢 Market Concentration (Sectors)")
        sector_stats = get_sector_stats()
        if sector_stats:
            # Using Polars for data processing
            df_sector = pl.DataFrame(sector_stats).head(8).to_pandas()
            fig = px.bar(
                df_sector,
                x="total",
                y="sector",
                orientation='h',
                color="total",
                color_continuous_scale="Viridis",
                labels={"total": "Count", "sector": "Sector"}
            )
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#FAFAFA',
                margin=dict(l=0, r=0, t=20, b=0),
                height=350,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("📍 Top Regions")
        region_stats = get_region_stats()
        if region_stats:
            df_region = pl.DataFrame(region_stats).head(10).to_pandas()
            st.dataframe(
                df_region,
                column_config={
                    "region": "Region",
                    "total": st.column_config.NumberColumn("Total Companies", format="%d 🏢")
                },
                use_container_width=True,
                hide_index=True
            )

    with col_right:
        st.subheader("🕒 Recent Activity")
        with st.container():
            timeline_event("New Batch Scraped", "2 hours ago", "Fetched 124 new companies from eInforma.", icon="🔄")
            timeline_event("API Enrichment Completed", "5 hours ago", "Successfully enriched 50 companies via NIF.pt API.", icon="✅")
            timeline_event("System Health Check", "Yesterday", "PostgreSQL database optimization performed.", icon="⚙️")
            timeline_event("Keyword Search Added", "2 days ago", "Added 'RESTAURAÇÃO' to automation keywords.", icon="🔍")

        st.subheader("🚀 Quick Actions")
        if st.button("📤 Export Full Database", use_container_width=True):
            st.toast("Exporting data...", icon="📄")
        if st.button("🧹 Clean Duplicates", use_container_width=True):
            st.toast("Cleaning data...", icon="✨")

    # Footer
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption(f"Last heartbeat: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Version 2.2.0-polars")

def main():
    # Simple Auth State
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        login_ui()
    else:
        # Sidebar Navigation
        with st.sidebar:
            st.markdown("""
                <div style="text-align: center; margin-bottom: 20px;">
                    <h1 style="font-size: 32px; margin-bottom: 0;">🇵🇹</h1>
                    <h3 style="margin-top: 5px;">PT Companies</h3>
                </div>
            """, unsafe_allow_html=True)

            st.markdown("---")

            if st.button("🚪 Logout", use_container_width=True):
                st.session_state["authenticated"] = False
                st.rerun()

            st.markdown("---")
            st.caption("Navigation through pages is handled via Streamlit's native sidebar menu.")

        main_dashboard()

if __name__ == "__main__":
    main()
