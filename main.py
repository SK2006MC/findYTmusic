# main.py
import asyncio
try:
    import pyperclip
except ImportError:
    pyperclip = None

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input

from config import Config
from models import AppState, SearchResult
from services import DatabaseService, Downloader, MusicSearchService
from ui import DetailsPane, LogPane, ResultsDisplay, SearchControls

class FindYTMusicApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"), 
        ("q", "quit", "Quit"), 
        ("c", "copy_link", "Copy Link"),
        ("l", "view_library", "View Library")
    ]
    CSS_PATH = "find_ytmusic.css"

    app_state = reactive(AppState(), always_update=True)

    def __init__(self, search_service: MusicSearchService, downloader: Downloader, db_service: DatabaseService, config: Config):
        super().__init__()
        self.search_service = search_service
        self.downloader = downloader
        self.db_service = db_service
        self.config = config

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            with Horizontal(id="app-grid"):
                with Vertical(id="left-pane"):
                    yield SearchControls()
                    yield ResultsDisplay(id="results-table")
                with Vertical(id="right-pane"):
                    yield DetailsPane(id="details-pane")
            yield LogPane(id="log", wrap=True, highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one(LogPane)
        self.query_one(Input).focus()
        if self.downloader.is_available:
            log.add_message(f"[green]✅ {self.config.DOWNLOAD_COMMAND} found.[/green]")
        else:
            log.add_message(f"[yellow]⚠️ '{self.config.DOWNLOAD_COMMAND}' not found.[/yellow]")
        if pyperclip:
            log.add_message("[green]✅ Clipboard found.[/green]")
        else:
            log.add_message("[yellow]⚠️ 'pyperclip' not installed.[/yellow]")
        self.action_view_library()

    def watch_app_state(self, old_state: AppState, new_state: AppState) -> None:
        if old_state.results != new_state.results:
            self.query_one(ResultsDisplay).update_results(new_state.results)
        self.query_one(DetailsPane).update_details(new_state.selected_result)

    def action_copy_link(self) -> None:
        log = self.query_one(LogPane)
        if not pyperclip:
            log.add_message("[red]❌ 'pyperclip' not installed.[/red]")
            return
        if self.app_state.selected_result:
            pyperclip.copy(self.app_state.selected_result.link)
            log.add_message(f"📋 Copied link for '[b]{self.app_state.selected_result.title}[/b]'.")
        else:
            log.add_message("[yellow]⚠️ No song selected.[/yellow]")

    def action_view_library(self) -> None:
        log = self.query_one(LogPane)
        log.add_message("📚 Loading full music library...")
        library_results = self.db_service.load_all_songs()
        self.app_state = AppState(results=library_results)
        log.add_message(f"💿 Displaying {len(library_results)} songs from your local library.")
        
    def on_search_controls_search_requested(self, message: SearchControls.SearchRequested) -> None:
        self.query_one(LogPane).add_message(f"🔎 Searching for '{message.query}'...")
        self.workers.cancel_group(self, "search_worker")
        self.run_worker(self.perform_search(message.query), group="search_worker", exclusive=True)

    def on_results_display_row_selected(self, message: ResultsDisplay.RowSelected) -> None:
        selected = next((r for r in self.app_state.results if r.video_id == message.key), None)
        if selected:
             self.run_worker(self.perform_download(selected), group="download_worker")

    def on_results_display_row_highlighted(self, message: ResultsDisplay.RowHighlighted) -> None:
        selected = next((r for r in self.app_state.results if r.video_id == message.key), None)
        self.app_state = AppState(results=self.app_state.results, selected_result=selected)

    async def perform_search(self, query: str) -> None:
        log = self.query_one(LogPane)
        results, error_details = await asyncio.to_thread(self.search_service.search, query, self.config.SEARCH_RESULT_LIMIT)
        if error_details:
            log.add_message(f"[red]❌ An error occurred during search.[/red]")
            log.add_message(f"[dim]{error_details}[/dim]")
            return
            
        self.app_state = AppState(results=results, selected_result=None)
        if not results:
            log.add_message(f"🤷 No music found for '{query}'.")
        else:
            log.add_message(f"🎶 Found {len(results)} results. New entries saved to local library.")

    async def perform_download(self, result: SearchResult) -> None:
        log = self.query_one(LogPane)
        if not self.downloader.is_available:
            log.add_message(f"[red]❌ Download failed: Command not found.[/red]")
            return
        log.add_message(f"📥 Queueing '[b]{result.title}[/b]' for download...")
        success, message = await asyncio.to_thread(self.downloader.run, result.link, result.title)
        if success:
            log.add_message(f"[green]✅ {message}[/green]")
        else:
            log.add_message(f"[red]❌ {message}[/red]")


if __name__ == "__main__":
    app_config = Config()
    db_service = DatabaseService(app_config.DATABASE_FILENAME)
    downloader_service = Downloader(app_config.DOWNLOAD_COMMAND)
    search_service = MusicSearchService(db_service)
    
    app = FindYTMusicApp(search_service, downloader_service, db_service, app_config)
    
    try:
        app.run()
    finally:
        db_service.close()