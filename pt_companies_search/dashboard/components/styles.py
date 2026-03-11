import streamlit as st
from datetime import datetime

def apply_custom_styles():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

        /* Main layout adjustments */
        .main {
            background-color: #0E1117;
            font-family: 'Inter', sans-serif;
        }
        
        /* Sidebar Styling */
        section[data-testid="stSidebar"] {
            background-color: #161B22;
            border-right: 1px solid #30363D;
        }
        
        /* Metric Card Styling (Native Streamlit override) */
        div[data-testid="stMetric"] {
            background-color: #1A1D24;
            border: 1px solid #30363D;
            padding: 15px 20px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        div[data-testid="stMetric"]:hover {
            transform: translateY(-4px);
            border-color: #58A6FF;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        }
        
        /* Custom Metric Card (for our HTML cards) */
        .metric-card {
            background-color: #1A1D24;
            border: 1px solid #30363D;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            height: 100%;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .metric-card:hover {
            transform: translateY(-4px);
            border-color: #58A6FF;
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        }
        .metric-label {
            font-size: 0.85rem;
            font-weight: 500;
            color: #8B949E;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #FAFAFA;
            line-height: 1.2;
        }
        .metric-delta {
            font-size: 0.8rem;
            font-weight: 600;
            margin-top: 8px;
            display: flex;
            align-items: center;
            gap: 4px;
        }
        .metric-delta.positive { color: #3FB950; }
        .metric-delta.negative { color: #F85149; }
        
        /* Tab Styling */
        .stTabs [data-baseweb="tab-list"] {
            gap: 24px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            padding-top: 10px;
            padding-bottom: 10px;
            background-color: transparent;
            border-bottom-width: 2px;
            color: #8B949E;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            color: #58A6FF !important;
            border-bottom-color: #58A6FF !important;
        }
        
        /* Custom Button Styling */
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            padding: 0.5rem 1rem;
            transition: all 0.2s;
            border: 1px solid #30363D;
            background-color: #21262D;
        }
        .stButton>button:hover {
            border-color: #8B949E;
            background-color: #30363D;
        }
        
        /* Status Indicator */
        .status-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.02em;
        }
        .status-online {
            background-color: rgba(35, 134, 54, 0.15);
            color: #3FB950;
            border: 1px solid rgba(63, 185, 80, 0.2);
        }
        .status-offline {
            background-color: rgba(218, 54, 51, 0.15);
            color: #F85149;
            border: 1px solid rgba(248, 81, 73, 0.2);
        }
        
        /* Typography */
        h1, h2, h3, h4 {
            font-family: 'Inter', -apple-system, sans-serif;
            font-weight: 700 !important;
            letter-spacing: -0.03em;
        }
        
        /* Dataframes */
        [data-testid="stDataFrame"] {
            border: 1px solid #30363D;
            border-radius: 12px;
            overflow: hidden;
        }

        /* Expander */
        .stExpander {
            border: 1px solid #30363D !important;
            border-radius: 12px !important;
            background-color: #161B22 !important;
        }
        </style>
    """, unsafe_allow_html=True)

def render_header(title, subtitle=None, icon="🇵🇹"):
    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        st.markdown(f"# {icon} {title}")
        if subtitle:
            st.markdown(f"<p style='color: #8B949E; font-size: 1.1rem; margin-top: -15px;'>{subtitle}</p>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
        # Status logic can be injected here or handled by the page

def render_footer():
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.caption(f"© {datetime.now().year} Portugal New Companies Tracker")
    with col2:
        st.markdown("<div style='text-align: right;'><span class='status-pill status-online'>● System Operational</span></div>", unsafe_allow_html=True)
