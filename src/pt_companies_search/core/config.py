import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root: src/pt_companies_search/core/ -> up 3 levels
load_dotenv(Path(__file__).parents[3] / ".env")


class Config:
    """Application configuration from environment variables."""

    # Database
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", 5432))
    DB_NAME: str = os.getenv("DB_NAME", "pt_companies")
    DB_USER: str = os.getenv("DB_USER", "pt_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "")

    @property
    def DB_URL(self) -> str:
        """PostgreSQL connection URL for Polars ADBC / connectorx."""
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # NIF.pt API
    NIF_API_KEY: str = os.getenv("NIF_API_KEY", "")

    # Scraper
    SCRAPER_DELAY: float = float(os.getenv("SCRAPER_DELAY", 2.0))
    SCRAPER_MAX_PAGES: int = int(os.getenv("SCRAPER_MAX_PAGES", 5))
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )


config = Config()
