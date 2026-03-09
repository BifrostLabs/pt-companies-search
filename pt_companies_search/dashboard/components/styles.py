import streamlit as st

def apply_custom_styles():
    st.markdown("""
        <style>
        /* Main layout adjustments */
        .main {
            background-color: #0E1117;
        }
        
        /* Metric Card Styling */
        div[data-testid="stMetric"] {
            background-color: #1A1D24;
            border: 1px solid #30363D;
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s ease-in-out;
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-2px);
            border-color: #58A6FF;
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #161B22;
            border-right: 1px solid #30363D;
        }
        
        /* Custom Button Styling */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s;
        }
        
        /* Table / Dataframe header */
        .stDataFrame th {
            background-color: #1A1D24 !important;
            color: #FAFAFA !important;
        }
        
        /* Status Indicator */
        .status-pill {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
        }
        .status-online {
            background-color: rgba(35, 134, 54, 0.2);
            color: #3FB950;
            border: 1px solid rgba(63, 185, 80, 0.3);
        }
        .status-offline {
            background-color: rgba(218, 54, 51, 0.2);
            color: #F85149;
            border: 1px solid rgba(248, 81, 73, 0.3);
        }
        
        /* Typography */
        h1, h2, h3 {
            font-family: 'Inter', -apple-system, sans-serif;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }
        
        /* Card Container for Custom UI */
        .custom-card {
            background-color: #1A1D24;
            border: 1px solid #30363D;
            padding: 20px;
            border-radius: 12px;
            margin-bottom: 20px;
        }
        
        /* Skeleton Loader Simulation */
        @keyframes shimmer {
            0% { background-position: -468px 0; }
            100% { background-position: 468px 0; }
        }
        .skeleton {
            height: 20px;
            background: #21262d;
            background-image: linear-gradient(to right, #21262d 0%, #30363d 20%, #21262d 40%, #21262d 100%);
            background-repeat: no-repeat;
            background-size: 800px 104px;
            display: inline-block;
            position: relative;
            animation: shimmer 1s linear infinite forwards;
        }
        </style>
    """, unsafe_allow_html=True)

def render_header(title, subtitle=None, icon="🇵🇹"):
    st.markdown(f"# {icon} {title}")
    if subtitle:
        st.markdown(f"*{subtitle}*")
    st.markdown("---")

def render_footer():
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"© {datetime.now().year} PT Companies Tracker")
    with col2:
        st.markdown("<div style='text-align: right;'><span class='status-pill status-online'>System Operational</span></div>", unsafe_allow_html=True)

from datetime import datetime
