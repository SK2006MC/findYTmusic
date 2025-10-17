# services.py
import shutil
import sqlite3
import subprocess
import traceback
from typing import List, Optional, Tuple

from ytmusicapi import YTMusic

from models import SearchResult

class DatabaseService:
    """A service to manage all SQLite database interactions."""
    def __init__(self, db_name: str):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.create_table()

    def create_table(self):
        """Creates the songs table if it doesn't exist."""
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS songs (
                    video_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    album_name TEXT,
                    duration TEXT,
                    link TEXT UNIQUE NOT NULL,
                    is_explicit BOOLEAN
                )
            """)

    def save_results(self, results: List[SearchResult]):
        """Saves a list of search results to the database, ignoring duplicates."""
        data_to_insert = [
            (r.video_id, r.title, r.artist, r.album_name, r.duration, r.link, r.is_explicit)
            for r in results
        ]
        with self.conn:
            self.conn.executemany("""
                INSERT OR IGNORE INTO songs 
                (video_id, title, artist, album_name, duration, link, is_explicit) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data_to_insert)

    def load_all_songs(self) -> List[SearchResult]:
        """Loads all songs from the database, sorted for display."""
        with self.conn:
            cursor = self.conn.execute(
                "SELECT * FROM songs ORDER BY artist, album_name, title"
            )
            return [SearchResult(**row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()


class Downloader:
    """A service to manage the external download command."""
    def __init__(self, command: str):
        self.command_name = command
        self.command_path = shutil.which(command)

    @property
    def is_available(self) -> bool:
        return self.command_path is not None

    def run(self, url: str, title: str) -> Tuple[bool, str]:
        """Runs the download command, returning success status and message."""
        if not self.is_available: return False, f"Command '{self.command_name}' not found."
        try:
            process = subprocess.run([self.command_path, url], check=True, capture_output=True, text=True, encoding='utf-8')
            return True, f"Download successful for '{title}'."
        except subprocess.CalledProcessError as e: return False, f"Download failed for '{title}'. Details:\n{e.stderr}"
        except Exception as e: return False, f"An unexpected error occurred during the download of '{title}': {e}"


class MusicSearchService:
    """A service to handle interactions with the ytmusicapi."""
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def search(self, query: str, limit: int) -> Tuple[Optional[List[SearchResult]], Optional[str]]:
        """Performs the search, saves results to DB, and returns them."""
        try:
            ytmusic = YTMusic()
            search_items = ytmusic.search(query=query, filter="songs", limit=limit)
            
            unique_results: dict[str, SearchResult] = {}
            for item in search_items:
                parsed_result = self._parse_item(item)
                if parsed_result and parsed_result.video_id:
                    unique_results[parsed_result.video_id] = parsed_result
            
            results = list(unique_results.values())
            if results:
                self.db_service.save_results(results)
            return results, None
        except Exception:
            return None, traceback.format_exc()

    def _parse_item(self, item: dict) -> Optional[SearchResult]:
        """Parses a single raw API item into our SearchResult data model."""
        if not item or "videoId" not in item:
            return None
            
        duration_seconds = item.get("duration_seconds")
        duration_formatted = "N/A"
        if duration_seconds is not None:
            minutes, seconds = divmod(duration_seconds, 60)
            duration_formatted = f"{minutes:02d}:{seconds:02d}"
        
        album = item.get("album")
        return SearchResult(
            video_id=item["videoId"],
            title=item.get("title", "N/A"),
            artist=", ".join([a["name"] for a in item.get("artists", [])]) or "N/A",
            album_name=album["name"] if album else "Single",
            duration=duration_formatted,
            link=f"https://music.youtube.com/watch?v={item['videoId']}",
            is_explicit=item.get("isExplicit", False),
        )