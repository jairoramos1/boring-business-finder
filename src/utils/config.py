"""
Configuration management for Boring Business Finder
"""
import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "output"
CONFIG_DIR = PROJECT_ROOT / "config"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@dataclass
class Config:
    """Application configuration"""
    
    # API Keys
    serpapi_key: Optional[str] = field(default_factory=lambda: os.getenv("SERPAPI_KEY"))
    apify_token: Optional[str] = field(default_factory=lambda: os.getenv("APIFY_API_TOKEN"))
    anthropic_key: Optional[str] = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY"))
    
    # Database
    database_path: Path = field(default_factory=lambda: DATA_DIR / "businesses.db")
    
    # Rate limiting
    requests_per_minute: int = 10
    delay_between_requests: float = 2.0
    
    # Scraping settings
    max_results_per_query: int = 100
    
    # Analysis thresholds
    min_reviews_for_analysis: int = 10
    high_opportunity_score: int = 70
    
    def __post_init__(self):
        """Validate configuration"""
        if not self.serpapi_key and not self.apify_token:
            print("⚠️  Warning: No scraping API key configured. Using demo mode.")
        
        if not self.anthropic_key:
            print("⚠️  Warning: No Anthropic API key. Using local sentiment analysis.")
    
    @property
    def has_scraping_api(self) -> bool:
        return bool(self.serpapi_key or self.apify_token)
    
    @property
    def has_ai_api(self) -> bool:
        return bool(self.anthropic_key)


# Global config instance
config = Config()
