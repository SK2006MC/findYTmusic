import sys
import asyncio
from dataclasses import dataclass

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import (Button, DataTable, Footer, Header, Input, Label,
                             Static)
from ytmusicapi import YTMusic

# --- Constants and Data Models ---

SEARCH_RESULT_LIMIT = 20

@dataclass
class SearchResult:
    """A data class to hold a single search result."""
    title: str
    artist: str
    duration: str
    link: str

# --- API Interaction Logic (Decoupled from UI) ---

def fetch_music_data(query: str) -> list[SearchResult]:
    """
    Performs the YouTube Music search and returns structured data.
    This function is UI-agnostic.
    """
    try:
        ytmusic = YTMusic()
        search_items = ytmusic.search(
            query=query, filter="songs", limit=SEARCH_RESULT_LIMIT
        )
        
        results = []
        for item in search_items:
            duration_seconds = item.get("duration_seconds")
            duration_formatted = "N/A"
            if duration_seconds is not None:
                minutes, seconds = divmod(duration_seconds, 60)
                duration_formatted = f"{minutes:02d}:{seconds:02d}"

            results.append(SearchResult(
                title=item.get("title", "N/A"),
                artist=", ".join(
                    [artist["name"] for artist in item.get("artists", [])]
                ) or "N/A",
                duration=duration_formatted,
                link=f"https://music.youtube.com/watch?v={item['videoId']}"
            ))
        return results
    except Exception:
        return []

# --- Custom UI Widgets ---

class SearchControls(Static):
    """A widget containing the search input and button."""

    class SearchRequested(Message):
        """A message sent when the user initiates a search."""
        def __init__(self, query: str) -> None:
            self.query = query
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("Enter your search terms:")
        yield Input(placeholder="e.g., Daft Punk - Get Lucky", id="search-input")
        yield Button("Search", id="search-button", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_search_message()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.post_search_message()

    def post_search_message(self) -> None:
        query = self.query_one(Input).value.strip()
        if query:
            self.post_message(self.SearchRequested(query))

class StatusBar(Static):
    """A simple status bar widget."""
    message = reactive("Ready.")

    def render(self) -> str:
        return self.message

    def update_status(self, text: str) -> None:
        self.message = text

class ResultsDisplay(DataTable):
    """A DataTable specialized for displaying search results."""
    def on_mount(self) -> None:
        self.add_columns("Title", "Artist", "Duration", "Link")

    def update_results(self, results: list[SearchResult]) -> None:
        self.clear()
        if results:
            self.add_rows(
                [(r.title, r.artist, r.duration, r.link) for r in results]
            )
        self.focus()

# --- Main Application Class ---

class FindYTMusicApp(App):
    """A Textual app to search YouTube Music, now acting as a coordinator."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
    ]
    CSS_PATH = "find_ytmusic.css"

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-container"):
            yield SearchControls()
            yield StatusBar(id="status")
            yield ResultsDisplay(id="results-table")
        yield Footer()
    
    def on_mount(self) -> None:
        self.query_one(SearchControls).query_one(Input).focus()

    def on_search_controls_search_requested(self, message: SearchControls.SearchRequested) -> None:
        status_bar = self.query_one(StatusBar)
        status_bar.update_status(f"Searching for '{message.query}'...")
        self.workers.cancel_group(self, "search_worker")
        self.run_worker(
            self.perform_search(message.query),
            group="search_worker"
        )

    # --- THIS IS THE CORRECTED PART ---
    async def perform_search(self, query: str) -> None:
        """Async worker method to fetch data and update UI safely."""
        results = await asyncio.to_thread(fetch_music_data, query)
        
        # In an async worker, you can call methods directly.
        # Textual ensures this runs on the main thread for you.
        self.update_ui_with_results(results, query)
    # --- END OF CORRECTION ---

    def update_ui_with_results(self, results: list[SearchResult], query: str) -> None:
        """Safely updates UI components from the main thread."""
        status_bar = self.query_one(StatusBar)
        results_table = self.query_one(ResultsDisplay)

        results_table.update_results(results)
        if not results:
            status_bar.update_status("No music found for your search terms.")
        else:
            status_bar.update_status(f"Found {len(results)} results for '{query}'.")


if __name__ == "__main__":
    app = FindYTMusicApp()
    app.run()