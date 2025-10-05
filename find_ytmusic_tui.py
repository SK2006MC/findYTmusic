import sys
import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Optional import for clipboard functionality
try:
    import pyperclip
except ImportError:
    pyperclip = None

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import (Button, DataTable, Footer, Header, Input, Label,
                             Markdown, RichLog, Static)
from ytmusicapi import YTMusic

# --- CONFIGURATION ---
@dataclass
class Config:
    """Holds all application configuration."""
    SEARCH_RESULT_LIMIT: int = 25
    DOWNLOAD_COMMAND: str = "gytmdl"

# --- DATA MODELS ---
@dataclass
class SearchResult:
    """A data class to hold all available details for a single result."""
    title: str
    artist: str
    duration: str
    link: str
    album_name: Optional[str] = None
    is_explicit: bool = False
    video_id: str = ""

# --- SERVICES (Business Logic Layer) ---
class Downloader:
    """A service to manage the external download command."""
    def __init__(self, command: str):
        self.command_name = command
        self.command_path = shutil.which(command)

    @property
    def is_available(self) -> bool:
        return self.command_path is not None

    def run(self, url: str) -> Tuple[bool, str]:
        """Runs the download command, returning success status and message."""
        if not self.is_available: return False, f"Command '{self.command_name}' not found."
        try:
            process = subprocess.run([self.command_path, url], check=True, capture_output=True, text=True)
            return True, "Download successful."
        except subprocess.CalledProcessError as e: return False, f"Download failed. Details:\n{e.stderr}"
        except Exception as e: return False, f"An unexpected error occurred: {e}"

class MusicSearchService:
    """A service to handle interactions with the ytmusicapi."""
    def search(self, query: str, limit: int) -> List[SearchResult]:
        """Performs the search and returns a list of structured results."""
        try:
            ytmusic = YTMusic()
            search_items = ytmusic.search(query=query, filter="songs", limit=limit)
            return [self._parse_item(item) for item in search_items]
        except Exception:
            return []

    def _parse_item(self, item: dict) -> SearchResult:
        """Parses a single raw API item into our SearchResult data model."""
        duration_seconds = item.get("duration_seconds")
        duration_formatted = "N/A"
        if duration_seconds is not None:
            minutes, seconds = divmod(duration_seconds, 60)
            duration_formatted = f"{minutes:02d}:{seconds:02d}"
        
        album = item.get("album")
        return SearchResult(
            title=item.get("title", "N/A"),
            artist=", ".join([a["name"] for a in item.get("artists", [])]) or "N/A",
            duration=duration_formatted,
            link=f"https://music.youtube.com/watch?v={item['videoId']}",
            album_name=album["name"] if album else "Single",
            is_explicit=item.get("isExplicit", False),
            video_id=item.get("videoId")
        )

# --- UI WIDGETS (Presentation Layer) ---
class SearchControls(Static):
    # ... (Unchanged)
    class SearchRequested(Message):
        def __init__(self, query: str) -> None: self.query = query; super().__init__()
    def compose(self) -> ComposeResult: yield Label("Enter search terms:"); yield Input(id="search-input"); yield Button("Search", variant="primary")
    def on_button_pressed(self, event: Button.Pressed) -> None: self.post_search_message()
    def on_input_submitted(self, event: Input.Submitted) -> None: self.post_search_message()
    def post_search_message(self) -> None:
        query = self.query_one(Input).value.strip()
        if query: self.post_message(self.SearchRequested(query))

class DetailsPane(Static):
    # ... (Unchanged)
    def on_mount(self) -> None: self.update_details(None)
    def update_details(self, result: Optional[SearchResult]) -> None:
        if result:
            content = f"## {result.title}\n\n- **Artist**: {result.artist}\n- **Album**: {result.album_name}\n- **Duration**: {result.duration}\n- **Explicit**: {'Yes' if result.is_explicit else 'No'}\n- **Link**: `{result.link}`"
        else: content = "## Details\n\n*Select a song to see its details.*"
        self.query_one(Markdown).update(content)
    def compose(self) -> ComposeResult: yield Markdown()

class ResultsDisplay(DataTable):
    # ... (Unchanged from the corrected version)
    class DownloadRequested(Message):
        def __init__(self, result: SearchResult) -> None: self.result = result; super().__init__()
    class ShowDetails(Message):
        def __init__(self, result: Optional[SearchResult]) -> None: self.result = result; super().__init__()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs); self._results_map: dict[str, SearchResult] = {}
    def on_mount(self) -> None: self.add_columns("Title", "Artist", "Album"); self.cursor_type = "row"
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        result = self._results_map.get(event.row_key.value)
        if result: self.post_message(self.DownloadRequested(result))
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        result = self._results_map.get(event.row_key.value)
        self.post_message(self.ShowDetails(result))
    def update_results(self, results: List[SearchResult]) -> None:
        self.clear(); self._results_map.clear()
        for r in results: self._results_map[r.video_id] = r; self.add_row(r.title, r.artist, r.album_name, key=r.video_id)
        self.focus()

class LogPane(RichLog):
    """A dedicated widget for logging application events."""
    def add_message(self, message: str) -> None:
        """Writes a new message to the log."""
        self.write(message)

# --- MAIN APPLICATION (Orchestration Layer) ---
class FindYTMusicApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("c", "copy_link", "Copy Link"),
    ]
    CSS_PATH = "find_ytmusic.css"

    def __init__(self):
        super().__init__()
        self.config = Config()
        self.downloader = Downloader(self.config.DOWNLOAD_COMMAND)
        self.search_service = MusicSearchService()

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Horizontal(id="app-grid"):
                with Vertical(id="left-pane"):
                    yield SearchControls()
                    yield ResultsDisplay(id="results-table")
                with Vertical(id="right-pane"):
                    yield DetailsPane(id="details-pane")
            yield LogPane(id="log", wrap=True, highlight=True)
        yield Footer()
    
    def on_mount(self) -> None:
        self.query_one(Input).focus()
        log = self.query_one(LogPane)
        if self.downloader.is_available: log.add_message(f"[green]✅ {self.config.DOWNLOAD_COMMAND} found.[/green] Press Enter to download.")
        else: log.add_message(f"[yellow]⚠️ '{self.config.DOWNLOAD_COMMAND}' not found. Download disabled.[/yellow]")
        if pyperclip: log.add_message("[green]✅ Clipboard found.[/green] Press 'c' to copy link.")
        else: log.add_message("[yellow]⚠️ 'pyperclip' not installed. Copying disabled.[/yellow]")

    def action_copy_link(self) -> None:
        log = self.query_one(LogPane)
        if not pyperclip: log.add_message("[red]❌ Cannot copy: 'pyperclip' library not installed.[/red]"); return
        result = self.query_one(ResultsDisplay)._results_map.get(self.query_one(ResultsDisplay).cursor_row_key)
        if result: pyperclip.copy(result.link); log.add_message(f"📋 Copied link for '[b]{result.title}[/b]'.")
        else: log.add_message("[yellow]⚠️ No song selected to copy.[/yellow]")

    # --- Message Handlers ---
    def on_search_controls_search_requested(self, message: SearchControls.SearchRequested) -> None:
        self.query_one(LogPane).add_message(f"🔎 Searching for '{message.query}'...")
        self.workers.cancel_group(self, "search_worker")
        self.run_worker(self.perform_search(message.query), group="search_worker")

    def on_results_display_download_requested(self, message: ResultsDisplay.DownloadRequested) -> None:
        log = self.query_one(LogPane)
        if not self.downloader.is_available: log.add_message(f"[red]❌ Cannot download.[/red]"); return
        log.add_message(f"📥 Queueing '[b]{message.result.title}[/b]' for download...")
        self.run_worker(self.perform_download(message.result), exclusive=True, group="download_worker")

    def on_results_display_show_details(self, message: ResultsDisplay.ShowDetails) -> None:
        self.query_one(DetailsPane).update_details(message.result)

    # --- Worker Methods ---
    async def perform_search(self, query: str) -> None:
        results = await asyncio.to_thread(self.search_service.search, query, self.config.SEARCH_RESULT_LIMIT)
        self.update_ui_with_results(results, query)

    async def perform_download(self, result: SearchResult) -> None:
        log = self.query_one(LogPane)
        log.add_message(f"⏳ Downloading '[b]{result.title}[/b]'...")
        success, message = await asyncio.to_thread(self.downloader.run, result.link)
        if success: log.add_message(f"[green]✅ Download complete for '[b]{result.title}[/b]'.[/green]")
        else: log.add_message(f"[red]❌ Download failed for '[b]{result.title}[/b]'.[/red]"); log.add_message(f"[dim]{message}[/dim]")

    def update_ui_with_results(self, results: List[SearchResult], query: str) -> None:
        self.query_one(ResultsDisplay).update_results(results)
        log = self.query_one(LogPane)
        if not results: log.add_message(f"🤷 No music found for '{query}'.")
        else: log.add_message(f"🎶 Found {len(results)} results for '{query}'.")

if __name__ == "__main__":
    app = FindYTMusicApp()
    app.run()