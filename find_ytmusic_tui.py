import sys
import asyncio
import shutil
import subprocess
from dataclasses import dataclass, field

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

# --- Configuration ---
SEARCH_RESULT_LIMIT = 25
DOWNLOAD_COMMAND = "gytmdl"

# --- Data Models ---
@dataclass
class SearchResult:
    """A data class to hold all available details for a single result."""
    title: str
    artist: str
    duration: str
    link: str
    album_name: str | None = None
    is_explicit: bool = False
    video_id: str = ""

# --- Service Classes ---
class Downloader:
    # ... (This class remains unchanged from the previous version)
    def __init__(self, command: str):
        self.command_name = command
        self.command_path = shutil.which(command)
    @property
    def is_available(self) -> bool: return self.command_path is not None
    def run(self, url: str) -> tuple[bool, str]:
        if not self.is_available: return False, f"Command '{self.command_name}' not found."
        try:
            process = subprocess.run([self.command_path, url], check=True, capture_output=True, text=True)
            return True, f"Successfully downloaded."
        except subprocess.CalledProcessError as e: return False, f"Download failed. Error:\n{e.stderr}"
        except Exception as e: return False, f"An unexpected error occurred: {e}"

def fetch_music_data(query: str) -> list[SearchResult]:
    """Performs the search and extracts all available details."""
    try:
        ytmusic = YTMusic()
        search_items = ytmusic.search(query=query, filter="songs", limit=SEARCH_RESULT_LIMIT)
        results = []
        for item in search_items:
            duration_seconds = item.get("duration_seconds")
            duration_formatted = "N/A"
            if duration_seconds is not None:
                minutes, seconds = divmod(duration_seconds, 60)
                duration_formatted = f"{minutes:02d}:{seconds:02d}"
            
            album = item.get("album")
            
            results.append(SearchResult(
                title=item.get("title", "N/A"),
                artist=", ".join([a["name"] for a in item.get("artists", [])]) or "N/A",
                duration=duration_formatted,
                link=f"https://music.youtube.com/watch?v={item['videoId']}",
                album_name=album["name"] if album else "Single",
                is_explicit=item.get("isExplicit", False),
                video_id=item.get("videoId")
            ))
        return results
    except Exception as e:
        print(e) # For debugging
        return []

# --- Custom UI Widgets ---
class SearchControls(Static):
    # ... (Unchanged)
    class SearchRequested(Message):
        def __init__(self, query: str) -> None: self.query = query; super().__init__()
    def compose(self) -> ComposeResult: yield Label("Enter your search terms:"); yield Input(id="search-input"); yield Button("Search", variant="primary")
    def on_button_pressed(self, event: Button.Pressed) -> None: self.post_search_message()
    def on_input_submitted(self, event: Input.Submitted) -> None: self.post_search_message()
    def post_search_message(self) -> None:
        query = self.query_one(Input).value.strip()
        if query: self.post_message(self.SearchRequested(query))

class DetailsPane(Static):
    """A widget to display all details of a selected song."""
    def on_mount(self) -> None:
        self.update_details(None)

    def update_details(self, result: SearchResult | None) -> None:
        """Update the content of the details pane."""
        if result:
            content = f"""
            ## {result.title}

            - **Artist**: {result.artist}
            - **Album**: {result.album_name}
            - **Duration**: {result.duration}
            - **Explicit**: {'Yes' if result.is_explicit else 'No'}
            - **Link**: `{result.link}`
            """
        else:
            content = "## Details\n\n*Select a song to see its details.*"
        
        # Using Markdown widget for rich formatting
        self.query_one(Markdown).update(content)

    def compose(self) -> ComposeResult:
        yield Markdown()

class ResultsDisplay(DataTable):
    """The results table, now smarter about its data."""
    # Custom messages for better communication
    class DownloadRequested(Message):
        def __init__(self, result: SearchResult) -> None: self.result = result; super().__init__()
    class ShowDetails(Message):
        def __init__(self, result: SearchResult | None) -> None: self.result = result; super().__init__()

    _results_map: dict[str, SearchResult] = field(default_factory=dict)

    def on_mount(self) -> None:
        self.add_columns("Title", "Artist", "Album")
        self.cursor_type = "row"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """When Enter is pressed, emit a DownloadRequested message."""
        result = self._results_map.get(event.row_key.value)
        if result: self.post_message(self.DownloadRequested(result))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        """When a row is highlighted, emit a ShowDetails message."""
        result = self._results_map.get(event.row_key.value)
        self.post_message(self.ShowDetails(result))

    def update_results(self, results: list[SearchResult]) -> None:
        self.clear()
        self._results_map.clear()
        for r in results:
            self._results_map[r.video_id] = r
            self.add_row(r.title, r.artist, r.album_name, key=r.video_id)
        self.focus()

# --- Main Application Class ---
class FindYTMusicApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("c", "copy_link", "Copy Link"),
    ]
    CSS_PATH = "find_ytmusic.css"

    def __init__(self):
        super().__init__()
        self.downloader = Downloader(DOWNLOAD_COMMAND)

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Horizontal(id="app-grid"):
                with Vertical(id="left-pane"):
                    yield SearchControls()
                    yield ResultsDisplay(id="results-table")
                with Vertical(id="right-pane"):
                    yield DetailsPane(id="details-pane")
            yield RichLog(id="log", wrap=True, highlight=True)
        yield Footer()
    
    def on_mount(self) -> None:
        self.query_one(Input).focus()
        log = self.query_one(RichLog)
        if self.downloader.is_available:
            log.write(f"[green]✅ {DOWNLOAD_COMMAND} found.[/green] Press Enter on a song to download.")
        else:
            log.write(f"[yellow]⚠️ '{DOWNLOAD_COMMAND}' not found. Download disabled.[/yellow]")
        if pyperclip:
            log.write("[green]✅ Clipboard found.[/green] Press 'c' on a song to copy its link.")
        else:
            log.write("[yellow]⚠️ 'pyperclip' not installed. Copying disabled.[/yellow]")

    def action_copy_link(self) -> None:
        """Action to copy the selected song's link to the clipboard."""
        log = self.query_one(RichLog)
        if not pyperclip:
            log.write("[red]❌ Cannot copy: 'pyperclip' library not installed.[/red]")
            return
        
        results_table = self.query_one(ResultsDisplay)
        result = results_table._results_map.get(results_table.cursor_row_key)
        if result:
            pyperclip.copy(result.link)
            log.write(f"📋 Copied link for '[b]{result.title}[/b]' to clipboard.")
        else:
            log.write("[yellow]⚠️ No song selected to copy.[/yellow]")

    # --- Message Handlers ---
    def on_search_controls_search_requested(self, message: SearchControls.SearchRequested) -> None:
        self.query_one(RichLog).write(f"🔎 Searching for '{message.query}'...")
        self.workers.cancel_group(self, "search_worker")
        self.run_worker(self.perform_search(message.query), group="search_worker")

    def on_results_display_download_requested(self, message: ResultsDisplay.DownloadRequested) -> None:
        log = self.query_one(RichLog)
        if not self.downloader.is_available:
            log.write(f"[red]❌ Cannot download: '{DOWNLOAD_COMMAND}' not found.[/red]")
            return
        log.write(f"📥 Queueing '[b]{message.result.title}[/b]' for download...")
        self.run_worker(self.perform_download(message.result), exclusive=True, group="download_worker")

    def on_results_display_show_details(self, message: ResultsDisplay.ShowDetails) -> None:
        self.query_one(DetailsPane).update_details(message.result)

    # --- Worker Methods ---
    async def perform_search(self, query: str) -> None:
        results = await asyncio.to_thread(fetch_music_data, query)
        self.update_ui_with_results(results, query)

    async def perform_download(self, result: SearchResult) -> None:
        log = self.query_one(RichLog)
        log.write(f"⏳ Downloading '[b]{result.title}[/b]'...")
        success, message = await asyncio.to_thread(self.downloader.run, result.link)
        if success:
            log.write(f"[green]✅ Successfully downloaded '[b]{result.title}[/b]'.[/green]")
        else:
            log.write(f"[red]❌ Download failed for '[b]{result.title}[/b]'.[/red]")
            log.write(f"[dim]{message}[/dim]") # Log the detailed error message

    def update_ui_with_results(self, results: list[SearchResult], query: str) -> None:
        self.query_one(ResultsDisplay).update_results(results)
        log = self.query_one(RichLog)
        if not results:
            log.write(f"🤷 No music found for '{query}'.")
        else:
            log.write(f"🎶 Found {len(results)} results for '{query}'.")

if __name__ == "__main__":
    app = FindYTMusicApp()
    app.run()