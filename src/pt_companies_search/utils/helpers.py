"""
Shared utilities for PT Companies Search
"""

import re
from typing import List

# Standard sector definitions
SECTORS = {
    "Construção": [
        "CONSTRUÇÕES", "CONSTRUÇÃO", "CONSTRUCTION", "OBRAS", "REMODELAÇÕES", "CIVIL",
        "EDIFICAÇÕES", "CONSTRUTORA", "HABITAÇÃO", "CARPINTARIA", "CANALIZAÇÃO",
        "ELECTRICIDADE", "ELETRICIDADE", "PINTURA", "SERRALHARIA", "ALUMÍNIOS",
        "TELHADOS", "BETÃO", "PAVIMENTOS", "ISOLAMENTOS", "MÁRMORES", "GRANITOS",
    ],
    "Tecnologia": [
        "TECH", "DIGITAL", "SOFTWARE", "INFORMÁTICA", "COMPUTER", "TECNOLOGIA",
        "IT ", "SISTEMAS", "SOLUTIONS", "SOLUÇÕES", "DATA", "INTELIGÊNCIA ARTIFICIAL",
        "LOGIC", "ANALYTICS", "PIXEL", "CLOUD", "CYBER", "WEB", "APP", "DEV",
        "PROGRAMAÇÃO", "AUTOMAÇÃO", "ROBÓTICA", "INOVAÇÃO",
    ],
    "Alimentação": [
        "FOOD", "RESTAURANTE", "CAFÉ", "BAR ", "HOTEL", "RESTAURAÇÃO", "ALIMENTAÇÃO",
        "COMIDAS", "BEBIDAS", "CHURRASQUEIRA", "PASTELARIA", "PADARIA", "SNACK",
        "CATERING", "GELADO", "PIZARIA", "PIZZARIA", "TASCO", "TABERNA",
    ],
    "Turismo": [
        "TURISMO", "TOURISM", "HOTEL", "HOSTEL", "ALOJAMENTO LOCAL", "SURF", "BEACH",
        "VIAGENS", "TRAVEL", "RESORT", "AVENTURA", "EXPERIÊNCIA", "TOURS",
    ],
    "Imobiliário": [
        "IMOBILIÁRIA", "IMÓVEIS", "PROPERTY", "REAL ESTATE", "ALOJAMENTO",
        "MEDIAÇÃO IMOBILIÁRIA", "PROPRIEDADES", "ESTATE", "ARRENDAMENTO",
    ],
    "Saúde": [
        "CLÍNICA", "CLINIC", "SAÚDE", "HEALTH", "MÉDICO", "DENTAL", "DENTISTA",
        "FARMÁCIA", "FISIOTERAPI", "ENFERMAGEM", "PSICOLOG", "VETERINÁRI",
        "ÓPTICA", "LABORAT", "DIAGNÓS",
    ],
    "Educação": [
        "ESCOLA", "EDUCAÇÃO", "ENSINO", "FORMAÇÃO", "ACADEMIA", "EXPLICAÇÕES",
        "COLÉGIO", "UNIVERSIDADE", "JARDIM DE INFÂNCIA", "CRECHE", "TRAINING",
    ],
    "Beleza": [
        "CABELEIREIRO", "ESTÉTICA", "BELEZA", "BEAUTY", "SPA", "NAIL", "BARBEIRO",
        "TATUAGEM", "MASSAGEM", "COSMÉTICA",
    ],
    "Consultoria": [
        "CONSULT", "CONSULTORIA", "GESTÃO", "ASSESSORIA", "MARKETING", "PUBLICIDADE",
        "ADVISORY", "ESTRATÉGIA", "RECURSOS HUMANOS", "CONTABILIDADE", "AUDITORIA",
        "JURÍDICO", "ADVOCACIA", "ADVOGADOS",
    ],
    "Transporte": [
        "TRANSPORT", "TRANSPORTE", "LOGÍSTICA", "LOGISTICA", "FRETAMENTO",
        "MUDANÇAS", "TÁXI", "COURIER", "ENTREGAS", "DISTRIBUIÇÃO", "MOTORISTA",
    ],
    "Comércio": [
        "COMÉRCIO", "COMERCIO", "LOJA", "SHOP", "STORE", "VENDA", "RETALHO",
        "IMPORTAÇÃO", "EXPORTAÇÃO", "TRADING", "ATACADO", "GROSSISTA",
    ],
}

# CAE prefix → sector (Portuguese activity classification codes)
CAE_SECTORS = {
    "Construção":   ["41", "42", "43"],
    "Tecnologia":   ["58", "62", "63"],
    "Alimentação":  ["10", "11", "56"],
    "Turismo":      ["55", "791", "799"],
    "Imobiliário":  ["68"],
    "Saúde":        ["86", "87", "88"],
    "Educação":     ["85"],
    "Beleza":       ["9602"],
    "Consultoria":  ["69", "70", "73", "74"],
    "Transporte":   ["49", "50", "51", "52", "53"],
    "Comércio":     ["45", "46", "47"],
    "Indústria":    ["13", "14", "15", "16", "17", "22", "23", "24", "25", "28", "29", "30"],
    "Agricultura":  ["01", "02", "03"],
}


def get_sector(name: str, cae: str = None) -> str:
    """Classify company into sector, preferring CAE code over name keywords."""
    # CAE-based classification (more accurate)
    if cae:
        cae_str = str(cae).strip()
        for sector, prefixes in CAE_SECTORS.items():
            if any(cae_str.startswith(p) for p in prefixes):
                return sector

    # Name keyword fallback
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
