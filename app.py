#!/usr/bin/env python3
"""
Portugal New Companies - Dashboard
Main entry point with home page as dashboard
Uses PostgreSQL when available, falls back to JSON
"""

import streamlit as st
from pathlib import Path
from datetime import datetime

# Import database loader
from db_loader import get_stats, is_db_available

# Set page config
st.set_page_config(
    page_title="Novas Empresas Portugal",
    page_icon="🇵🇹",
    layout="wide"
)


def home():
    """Home page - Dashboard Overview"""
    
    # Center content
    _, col_main, _ = st.columns([0.05, 0.9, 0.05])
    
    with col_main:
        # Header
        st.title("🇵🇹 Novas Empresas")
        st.markdown("### Sistema de Rastreamento e Enriquecimento de Empresas")
        
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
