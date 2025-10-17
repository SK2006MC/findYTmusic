# models.py
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class SearchResult:
    """A data class to hold all available details for a single result."""
    video_id: str
    title: str
    artist: str
    album_name: str
    duration: str
    link: str
    is_explicit: bool

@dataclass
class AppState:
    """A single object to hold the entire application state."""
    results: List[SearchResult] = field(default_factory=list)
    selected_result: Optional[SearchResult] = None