import sys
import asyncio
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

# Optional import for clipboard functionality
try:
    import pyperclip
except ImportError:
    pyperclip = None

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (Button, DataTable, Footer, Header, Input, Label,
                             Markdown, RichLog, Static)
from ytmusicapi import YTMusic

# --- CONFIGURATION ---
@dataclass
class Config:
    """Holds all application configuration."""
    SEARCH_RESULT_LIMIT: int = 25
    DOWNLOAD_COMMAND: str = "gytmdl"

# --- DATA MODELS & STATE ---
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

@dataclass
class AppState:
    """A single object to hold the entire application state."""
    results: List[SearchResult] = field(default_factory=list)
    selected_result: Optional[SearchResult] = None

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
        """Performs the search and returns a list of unique, structured results."""
        try:
            ytmusic = YTMusic()
            search_items = ytmusic.search(query=query, filter="songs", limit=limit)
            
            unique_results: dict[str, SearchResult] = {}
            for item in search_items:
                parsed_result = self._parse_item(item)
                if parsed_result.video_id:
                    unique_results[parsed_result.video_id] = parsed_result
            
            return list(unique_results.values())
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
    """Widget for the search input and button."""
    class SearchRequested(Message):
        def __init__(self, query: str) -> None: self.query = query; super().__init__()
    def compose(self) -> ComposeResult: yield Label("Enter search terms:"); yield Input(id="search-input"); yield Button("Search", variant="primary")
    def on_button_pressed(self, event: Button.Pressed) -> None: self.post_search_message()
    def on_input_submitted(self, event: Input.Submitted) -> None: self.post_search_message()
    def post_search_message(self) -> None:
        query = self.query_one(Input).value.strip()
        if query: self.post_message(self.SearchRequested(query))

class DetailsPane(Static):
    """Widget to display details of the selected song."""
    def on_mount(self) -> None: self.update_details(None)
    def update_details(self, result: Optional[SearchResult]) -> None:
        if result: content = f"## {result.title}\n\n- **Artist**: {result.artist}\n- **Album**: {result.album_name}\n- **Duration**: {result.duration}\n- **Explicit**: {'Yes' if result.is_explicit else 'No'}\n- **Link**: `{result.link}`"
        else: content = "## Details\n\n*Select a song to see its details.*"
        self.query_one(Markdown).update(content)
    def compose(self) -> ComposeResult: yield Markdown()

class ResultsDisplay(DataTable):
    """Widget for the main results table."""
    class RowSelected(Message):
        def __init__(self, key: str) -> None: self.key = key; super().__init__()
    class RowHighlighted(Message):
        def __init__(self, key: Optional[str]) -> None: self.key = key; super().__init__()
    def on_mount(self) -> None: self.add_columns("Title", "Artist", "Album"); self.cursor_type = "row"
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None: self.post_message(self.RowSelected(event.row_key.value))
    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None: self.post_message(self.RowHighlighted(event.row_key.value))
    def update_results(self, results: List[SearchResult]) -> None:
        self.clear()
        for r in results: self.add_row(r.title, r.artist, r.album_name, key=r.video_id)
        self.focus()

class LogPane(RichLog):
    """A dedicated widget for logging application events."""
    def add_message(self, message: str) -> None:
        self.write(message)

# --- MAIN APPLICATION (Orchestration Layer) ---
class FindYTMusicApp(App):
    BINDINGS = [("d", "toggle_dark", "Toggle dark mode"), ("q", "quit", "Quit"), ("c", "copy_link", "Copy Link")]
    CSS_PATH = "find_ytmusic.css"

    app_state = reactive(AppState())

    def __init__(self, search_service: MusicSearchService, downloader: Downloader, config: Config):
        super().__init__()
        self.search_service = search_service
        self.downloader = downloader
        self.config = config

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Horizontal(id="app-grid"):
                with Vertical(id="left-pane"): yield SearchControls(); yield ResultsDisplay(id="results-table")
                with Vertical(id="right-pane"): yield DetailsPane(id="details-pane")
            yield LogPane(id="log", wrap=True, highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        self.query_one(Input).focus(); log = self.query_one(LogPane)
        if self.downloader.is_available: log.add_message(f"[green]✅ {self.config.DOWNLOAD_COMMAND} found.[/green]")
        else: log.add_message(f"[yellow]⚠️ '{self.config.DOWNLOAD_COMMAND}' not found.[/yellow]")
        if pyperclip: log.add_message("[green]✅ Clipboard found.[/green]")
        else: log.add_message("[yellow]⚠️ 'pyperclip' not installed.[/yellow]")

    def watch_app_state(self, old_state: AppState, new_state: AppState) -> None:
        """The heart of the reactive UI. Pushes state changes to child widgets."""
        if old_state.results != new_state.results:
            self.query_one(ResultsDisplay).update_results(new_state.results)
        self.query_one(DetailsPane).update_details(new_state.selected_result)

    def action_copy_link(self) -> None:
        log = self.query_one(LogPane)
        if not pyperclip: log.add_message("[red]❌ 'pyperclip' not installed.[/red]"); return
        if self.app_state.selected_result:
            pyperclip.copy(self.app_state.selected_result.link)
            log.add_message(f"📋 Copied link for '[b]{self.app_state.selected_result.title}[/b]'.")
        else: log.add_message("[yellow]⚠️ No song selected.[/yellow]")

    # --- Message Handlers ---
    def on_search_controls_search_requested(self, message: SearchControls.SearchRequested) -> None:
        self.query_one(LogPane).add_message(f"🔎 Searching for '{message.query}'...")
        self.workers.cancel_group(self, "search_worker")
        self.run_worker(self.perform_search(message.query), group="search_worker")

    def on_results_display_row_selected(self, message: ResultsDisplay.RowSelected) -> None:
        """Handles download request based on the unique key from the DataTable."""
        selected = next((r for r in self.app_state.results if r.video_id == message.key), None)
        if selected:
             self.run_worker(self.perform_download(selected), exclusive=True, group="download_worker")

    def on_results_display_row_highlighted(self, message: ResultsDisplay.RowHighlighted) -> None:
        """Updates the selected_result in the central state."""
        selected = next((r for r in self.app_state.results if r.video_id == message.key), None)
        self.app_state = AppState(results=self.app_state.results, selected_result=selected)

    # --- Worker Methods ---
    async def perform_search(self, query: str) -> None:
        results = await asyncio.to_thread(self.search_service.search, query, self.config.SEARCH_RESULT_LIMIT)
        self.app_state = AppState(results=results, selected_result=None)
        log = self.query_one(LogPane)
        if not results: log.add_message(f"🤷 No music found for '{query}'.")
        else: log.add_message(f"🎶 Found {len(results)} results for '{query}'.")

    async def perform_download(self, result: SearchResult) -> None:
        log = self.query_one(LogPane)
        if not self.downloader.is_available:
            log.add_message(f"[red]❌ Download failed: Command not found.[/red]")
            return
        log.add_message(f"📥 Queueing '[b]{result.title}[/b]' for download...")
        success, message = await asyncio.to_thread(self.downloader.run, result.link)
        if success: log.add_message(f"[green]✅ Download complete for '[b]{result.title}[/b]'.[/green]")
        else: log.add_message(f"[red]❌ Download failed.[/red]"); log.add_message(f"[dim]{message}[/dim]")

if __name__ == "__main__":
    # --- Application Entry Point ---
    # Here, we instantiate our services and inject them into the app.
    app_config = Config()
    downloader_service = Downloader(app_config.DOWNLOAD_COMMAND)
    search_service = MusicSearchService()
    
    app = FindYTMusicApp(search_service, downloader_service, app_config)
    app.run()