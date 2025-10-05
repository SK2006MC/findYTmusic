import sys
import argparse
# No special worker imports are needed for this method
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, Button, DataTable, Static, Label
from textual.containers import Container, Vertical
from textual.reactive import reactive
from ytmusicapi import YTMusic

# Initialize YTMusic globally
ytmusic = YTMusic()

class FindYTMusicApp(App):
    """A Textual app to search YouTube Music."""

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit_app", "Quit"),
    ]

    CSS_PATH = "find_ytmusic.css"

    search_results = reactive([])
    status_message = reactive("Ready.")

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        with Container(id="main-container"):
            with Vertical(id="search-area"):
                yield Label("Enter your search terms:")
                yield Input(placeholder="e.g., Bohemian Rhapsody Queen", id="search-input")
                yield Button("Search", id="search-button", variant="primary")
            
            yield Static(id="status", classes="message")
            
            yield DataTable(id="results-table", zebra_stripes=True)

        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted."""
        self.query_one(DataTable).add_columns("Title", "Artist", "Duration", "Link")
        self.query_one("#search-input").focus()

    # This is now a standard method that will be run in the background
    def run_ytmusic_search(self, query: str, limit: int = 10):
        """
        This function runs in a background thread via self.run_worker.
        It performs the search and prepares the data.
        """
        # To update the UI from this background thread, we must use self.call_from_thread
        self.call_from_thread(self.set_status, f"Searching for '{query}'...")
        try:
            search_items = ytmusic.search(query=query, filter="songs", limit=limit)
            
            results_data = []
            for item in search_items:
                title = item.get("title", "N/A")
                artists = ", ".join([artist["name"] for artist in item.get("artists", [])]) if item.get("artists") else "N/A"
                link = f"https://music.youtube.com/watch?v={item['videoId']}"
                
                duration_seconds = item.get("duration_seconds")
                duration_formatted = "N/A"
                if duration_seconds is not None:
                    minutes = duration_seconds // 60
                    seconds = duration_seconds % 60
                    duration_formatted = f"{minutes:02d}:{seconds:02d}"

                results_data.append((title, artists, duration_formatted, link))
            
            # Safely schedule the UI update on the main thread
            self.call_from_thread(self.update_results, results_data, query)

        except Exception as e:
            # Safely schedule the error message update on the main thread
            self.call_from_thread(self.set_status, f"[red]Error during search: {e}[/red]")
            self.call_from_thread(setattr, self, "search_results", [])

    def set_status(self, message: str) -> None:
        """Helper method to safely set the status_message reactive variable."""
        self.status_message = message

    def update_results(self, results: list, query: str) -> None:
        """Helper method to safely update results and status."""
        self.search_results = results
        if not results:
            self.status_message = "No music found for your search terms."
        else:
            self.status_message = f"Found {len(results)} results for '{query}'."

    def watch_search_results(self, results_data: list) -> None:
        """Called when self.search_results changes."""
        table = self.query_one(DataTable)
        table.clear()
        if results_data:
            table.add_rows(results_data)
        table.focus()

    def watch_status_message(self, message: str) -> None:
        """Called when self.status_message changes."""
        self.query_one("#status", Static).update(message)

    def action_quit_app(self) -> None:
        self.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "search-button":
            self.trigger_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self.trigger_search()

    def trigger_search(self) -> None:
        """Initiate the search by creating a background worker."""
        query = self.query_one("#search-input", Input).value.strip()
        if query:
            # Cancel any previous searches to avoid race conditions
            self.workers.cancel_group(self, "search_worker")
            
            # --- THIS IS THE CORRECTED PART ---
            # The 'query' argument is now passed positionally.
            # The optional arguments 'group' and 'name' are passed with keywords.
            self.run_worker(
                self.run_ytmusic_search,
                query,  # Positional argument for run_ytmusic_search
                group="search_worker",
                name=f"Searching for {query}"
            )
            # --- END OF CORRECTION ---
            
        else:
            self.status_message = "[orange3]Please enter search terms.[/orange3]"
            self.query_one("#search-input").focus()


if __name__ == "__main__":
    app = FindYTMusicApp()
    app.run()