import os
from typing import Dict, Any

class Config:
    """Configuration management using environment variables"""
    
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 5432))
    DB_NAME = os.getenv("DB_NAME", "pt_companies")
    DB_USER = os.getenv("DB_USER", "pt_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "pt_secure_pass_2024")

    @property
    def DB_CONFIG(self) -> Dict[str, Any]:
        return {
            "host": self.DB_HOST,
            "port": self.DB_PORT,
            "database": self.DB_NAME,
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
        }

    # NIF.pt API
    NIF_API_KEY = os.getenv("NIF_API_KEY", "")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    
    # Scraper Settings
    SCRAPER_DELAY = float(os.getenv("SCRAPER_DELAY", 2.0))
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

config = Config()
