# config.py
from dataclasses import dataclass

@dataclass
class Config:
    """Holds all application configuration."""
    SEARCH_RESULT_LIMIT: int = 25
    DOWNLOAD_COMMAND: str = "gytmdl"
    DATABASE_FILENAME: str = "ytmusic_library.db"