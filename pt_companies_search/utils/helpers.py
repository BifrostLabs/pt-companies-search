"""
Shared utilities for PT Companies Search
"""

import re
from typing import List

# Standard sector definitions
SECTORS = {
    "🏗️ Construção": ["CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL", "EDIFICAÇÕES", "CONSTRUTORA", "HABITAÇÃO"],
    "💻 Tecnologia/TI": ["TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA", "IT ", "SISTEMAS", "SOLUTIONS", "SOLUÇÕES", "DATA", "INTELIGÊNCIA ARTIFICIAL", "LOGIC"],
    "🍽️ Alimentação": ["FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "TURISMO", "RESTAURAÇÃO", "ALIMENTAÇÃO", "COMIDAS", "BEBIDAS", "CHURRASQUEIRA"],
    "🏠 Imobiliário": ["IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO", "MEDIÇÃO IMOBILIÁRIA", "MEDIAÇÃO IMOBILIÁRIA", "PROPRIEDADES", "ESTATE"],
    "💼 Consultoria": ["CONSULT", "CONSULTORIA", "SERVIÇOS", "GESTÃO", "ASSESSORIA", "MARKETING", "PUBLICIDADE", "ADVISORY"],
}

def get_sector(name: str) -> str:
    """Classify company into sector"""
    if not name:
        return "Outro"
    name_upper = name.upper()
    for sector, keywords in SECTORS.items():
        if any(kw in name_upper for kw in keywords):
            return sector
    return "Outro"

def extract_city(location: str) -> str:
    """Extract city from location string (e.g., '1000-001 LISBOA')"""
    if not location or location == "N/A":
        return ""
    parts = location.split(maxsplit=1)
    if len(parts) > 1:
        return parts[1]
    return ""

def extract_postal_code(location: str) -> str:
    """Extract postal code from location string"""
    if not location or location == "N/A":
        return ""
    parts = location.split(maxsplit=1)
    if len(parts) > 0:
        return parts[0]
    return ""
