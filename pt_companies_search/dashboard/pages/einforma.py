#!/usr/bin/env python3
"""
eInforma.pt - Novas Empresas (Refactored UI/UX with Polars)
"""

import streamlit as st
import polars as pl
from datetime import datetime
import plotly.express as px

# Check connection and imports
try:
    from pt_companies_search.core.database import (
        is_db_available, get_einforma_dataframe, load_enriched_data
    )
    from pt_companies_search.dashboard.components.styles import apply_custom_styles, render_header, render_footer
    from pt_companies_search.dashboard.components.cards import metric_card, section_header
except ImportError as e:
    st.error(f"Import Error: {e}. Check directory structure and PYTHONPATH.")
    st.stop()

# Config
st.set_page_config(
    page_title="eInforma.pt - PT Companies",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply global custom styles
apply_custom_styles()

# Standard sector definitions
SECTORS = {
    "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL"],
    "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS"],
    "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO"],
    "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO", "MEDIÇÃO IMOBILIÁRIA"],
    "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA"],
}

@st.cache_data(ttl=3600)
def load_data():
    """Load data from database"""
    df = get_einforma_dataframe(use_historical=True)
    enriched_data = load_enriched_data()
    return df, enriched_data

def merge_enriched_data(df, enriched_dict):
    """Merge enriched data into dataframe"""
    if not enriched_dict or df.is_empty():
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
    
    enriched_df = pl.DataFrame(enriched_rows)
    return df.join(enriched_df, on="nif", how="left")

def render_sidebar(df, enriched_data):
    """Render sidebar filters"""
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 25px; background: #1A1D24; padding: 20px; border-radius: 12px; border: 1px solid #30363D;">
                <h1 style="font-size: 40px; margin-bottom: 0;">📋</h1>
                <h3 style="margin-top: 10px; font-weight: 700;">eInforma.pt</h3>
                <p style="color: #8B949E; font-size: 0.8rem;">Data Source Explorer</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 🔍 Filters")
        
        # Search Filter
        search = st.text_input("Search Company", "", placeholder="Name or NIF...").strip().lower()
        
        # Date Filter
        if "registration_date" in df.columns:
            # Drop nulls for min/max calculation
            dates = df.select("registration_date").drop_nulls()
            if not dates.is_empty():
                min_date = dates.min().item()
                max_date = dates.max().item()
                date_range = st.date_input("Registration Period", value=(min_date, max_date))
            else:
                date_range = None
        else:
            date_range = None
        
        # Sector Filter
        selected_sectors = st.multiselect("Filter by Sector", list(SECTORS.keys()), placeholder="All Sectors")
        
        # Enriched Only Toggle
        show_enriched_only = False
        if enriched_data:
            # Count how many NIFs in df are also in enriched_data
            df_nifs = set(df.select("nif").to_series().to_list())
            enriched_nifs_in_df = [nif for nif in df_nifs if nif in enriched_data]
            enriched_count = len(enriched_nifs_in_df)
            show_enriched_only = st.checkbox(f"✨ Enriched Only ({enriched_count})", help="Show only companies with extra contact info.")
        
        st.markdown("---")
        
        # Actions
        st.markdown("### ⚡ Actions")
        if st.button("🔄 Refresh Cache", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
            
        # Export Option
        csv = df.to_pandas().to_csv(index=False).encode("utf-8")
        st.download_button(
            "📄 Export Filtered CSV",
            csv,
            f"einforma_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
            use_container_width=True
        )
        
        st.markdown("---")
        st.caption(f"Last heartbeat: {datetime.now().strftime('%H:%M:%S')}")

    return {
        "search": search,
        "date_range": date_range,
        "show_enriched_only": show_enriched_only,
        "sectors": selected_sectors,
    }

def apply_filters(df, filters, enriched_data):
    """Apply filters to dataframe"""
    filtered_df = df
    
    if filters["date_range"] and isinstance(filters["date_range"], (tuple, list)) and len(filters["date_range"]) == 2:
        start_date, end_date = filters["date_range"]
        if "registration_date" in filtered_df.columns:
            filtered_df = filtered_df.filter(
                (pl.col("registration_date") >= start_date) & 
                (pl.col("registration_date") <= end_date)
            )
    
    if filters["search"]:
        s = filters["search"]
        filtered_df = filtered_df.filter(
            (pl.col("name").str.to_lowercase().str.contains(s)) |
            (pl.col("nif").str.to_lowercase().str.contains(s))
        )
    
    if filters["sectors"]:
        all_keywords = []
        for sector in filters["sectors"]:
            all_keywords.extend(SECTORS.get(sector, []))
        if all_keywords:
            # Join keywords with | for regex
            regex_pattern = "(?i)" + "|".join(all_keywords)
            filtered_df = filtered_df.filter(
                pl.col("name").str.contains(regex_pattern)
            )
    
    if filters["show_enriched_only"] and enriched_data:
        enriched_nifs = list(enriched_data.keys())
        filtered_df = filtered_df.filter(pl.col("nif").is_in(enriched_nifs))
    
    return filtered_df

def main():
    # Header area
    render_header("eInforma.pt - Novas Empresas", "Detailed view of newly registered companies in Portugal.")

    # Load data
    df, enriched_data = load_data()
    
    if df.is_empty():
        st.error("Nenhum dado encontrado. Execute o scraper primeiro.")
        st.stop()
    
    # Merge enriched data
    if enriched_data:
        df = merge_enriched_data(df, enriched_data)
    
    # Render sidebar
    filters = render_sidebar(df, enriched_data)
    
    # Apply filters
    filtered_df = apply_filters(df, filters, enriched_data)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Total Companies", f"{len(df):,}", icon="🏢")
    with col2:
        metric_card("Filtered Results", f"{len(filtered_df):,}", icon="🔍")
    with col3:
        # Count enriched in filtered results
        if enriched_data and not filtered_df.is_empty():
            enriched_count = filtered_df.filter(pl.col("nif").is_in(list(enriched_data.keys()))).height
        else:
            enriched_count = 0
        metric_card("Enriched Data", f"{enriched_count:,}", icon="✨")
    with col4:
        date_count = filtered_df.select("registration_date").n_unique() if "registration_date" in filtered_df.columns else 0
        metric_card("Unique Dates", f"{date_count}", icon="📅")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Improved Data Table
    section_header("Browse Data", icon="📊")
    
    # Custom column configuration
    display_df = filtered_df.to_pandas()
    
    # Create NIF link
    if "nif" in display_df.columns:
        display_df["nif_link"] = display_df["nif"].apply(lambda x: f"https://www.nif.pt/{x}/")

    # Rename columns for display
    display_df = display_df.rename(columns={
        "registration_date": "Date",
        "nif": "NIF",
        "name": "Company Name",
        "enriched_phone": "Phone",
        "enriched_email": "Email",
        "enriched_city": "City"
    })
    
    column_config = {
        "nif_link": st.column_config.LinkColumn("NIF", display_text=r"https://www.nif.pt/(.+)/", width="small"),
        "Company Name": st.column_config.TextColumn("Company Name", width="large"),
        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
        "Email": st.column_config.LinkColumn("Email", width="medium"),
        "Phone": st.column_config.TextColumn("Phone", width="small"),
        "City": st.column_config.TextColumn("City", width="small"),
    }
    
    # Add highlighting column
    if enriched_data:
        display_df["✨"] = display_df["NIF"].apply(lambda x: "✅" if x in enriched_data else "")
        column_config["✨"] = st.column_config.TextColumn("✨", width="extra-small")
        # Reorder to put status first
        cols = ["✨", "Date", "nif_link", "Company Name"]
    else:
        cols = ["Date", "nif_link", "Company Name"]
        
    # Add enriched cols if available
    for c in ["Phone", "Email", "City"]:
        if c in display_df.columns:
            cols.append(c)
            
    st.dataframe(
        display_df[cols], 
        use_container_width=True, 
        height=600,
        column_config=column_config,
        hide_index=True
    )
    
    render_footer()

if __name__ == "__main__":
    main()
