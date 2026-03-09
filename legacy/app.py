#!/usr/bin/env python3
"""
Portugal New Companies - Dashboard
Main entry point with home page as dashboard
Uses PostgreSQL when available, falls back to JSON
Auto-refreshes every 30 seconds
"""

import streamlit as st
from pathlib import Path
from datetime import datetime
import time

# Import database loader
from db_loader import get_stats, is_db_available

# Set page config
st.set_page_config(
    page_title="Novas Empresas Portugal",
    page_icon="🇵🇹",
    layout="wide",
    initial_sidebar_state="collapsed"
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


def home():
    """Home page - Dashboard Overview"""
    
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
        # Header
        st.title("🇵🇹 Novas Empresas")
        st.markdown("### Sistema de Rastreamento e Enriquecimento de Empresas")
        
        # Show last update time
        st.caption(f"Última atualização: {datetime.now().strftime('%H:%M:%S')}")
        
        # Add a refresh button to clear cache manually
        if st.button("🔄 Forçar Atualização de Dados"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Statistics (auto-loads from DB or JSON)
        stats = get_stats()
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "📋 Total", 
                f"{stats['einforma_total']:,}",
                "empresas"
            )
        
        with col2:
            st.metric(
                "📊 Enriquecidos", 
                f"{stats['enriched_total']:,}",
                "via API"
            )
        
        with col3:
            st.metric(
                "📞 Com Contacto", 
                f"{stats['enriched_with_contact']:,}",
                "telefone/email"
            )
        
        with col4:
            st.metric(
                "🔍 Pesquisados", 
                f"{stats['search_total']:,}",
                "via scraping"
            )
        
        st.markdown("---")
        
        # Quick Navigation
        st.markdown("## 📊 Fontes de Dados")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            ### 📋 eInforma.pt
            
            Empresas recém-registradas em Portugal com dados básicos:
            - NIF e nome
            - Data de registro
            - Link oficial
            
            ```bash
            pt-scrape  # Atualizar dados
            ```
            """)
            if st.button("📋 Aceder eInforma.pt", use_container_width=True):
                st.switch_page("pages/einforma.py")
        
        with col2:
            st.markdown("""
            ### 📊 NIF.pt
            
            Dados enriquecidos de contacto:
            - Telefone, email, website
            - Morada completa
            - CAE e status
            
            ```bash
            pt-nif-enrich --source historical
            ```
            """)
            if st.button("📊 Aceder NIF.pt", use_container_width=True):
                st.switch_page("pages/nif.py")
        
        st.markdown("---")
        
        # Commands
        with st.expander("🚀 Comandos Disponíveis"):
            st.markdown("""
            #### Pesquisa
            ```bash
            pt-nif-search "RESTAURANTE"   # Pesquisar no NIF.pt
            pt-search tech                # Pesquisar local
            pt-latest                     # Últimas empresas
            ```
            
            #### Enriquecimento
            ```bash
            pt-nif-enrich --source historical  # Enriquecer todas
            pt-nif-enrich --nif 509442013      # Empresa específica
            pt-nif-enrich --status             # Ver rate limits
            ```
            
            #### Dashboard
            ```bash
            pt-dashboard     # Abrir dashboard
            pt-db-up         # Iniciar PostgreSQL
            pt-db-migrate    # Migrar para DB
            ```
            """)
        
        st.markdown("---")
        st.caption("Desenvolvido com ❤️ by EasyTask.pt")


# Navigation - home is default
pg = st.navigation([
    st.Page(home, title="Home", icon="🏠", default=True),
    st.Page("pages/einforma.py", title="eInforma.pt", icon="📋"),
    st.Page("pages/nif.py", title="NIF.pt", icon="📊"),
])

pg.run()
