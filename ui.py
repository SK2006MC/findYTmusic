# ui.py
from typing import List, Optional

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import (Button, DataTable, Input, Label, Markdown, RichLog,
                             Static)

from models import SearchResult

class SearchControls(Static):
    """Widget for the search input and button."""
    class SearchRequested(Message):
        def __init__(self, query: str) -> None: 
            self.query = query
            super().__init__()

    def compose(self) -> ComposeResult:
        yield Label("Enter search terms:")
        yield Input(id="search-input")
        yield Button("Search", variant="primary")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.post_search_message()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.post_search_message()

    def post_search_message(self) -> None:
        query = self.query_one(Input).value.strip()
        if query:
            self.post_message(self.SearchRequested(query))


class DetailsPane(Static):
    """Widget to display details of the selected song."""
    def on_mount(self) -> None:
        self.update_details(None)

    def update_details(self, result: Optional[SearchResult]) -> None:
        if result:
            content = f"## {result.title}\n\n- **Artist**: {result.artist}\n- **Album**: {result.album_name}\n- **Duration**: {result.duration}\n- **Explicit**: {'Yes' if result.is_explicit else 'No'}\n- **Link**: `{result.link}`"
        else:
            content = "## Details\n\n*Select a song to see its details.*"
        self.query_one(Markdown).update(content)

    def compose(self) -> ComposeResult:
        yield Markdown()


class ResultsDisplay(DataTable):
    """Widget for the main results table."""
    class RowSelected(Message):
        def __init__(self, key: str) -> None: 
            self.key = key
            super().__init__()

    class RowHighlighted(Message):
        def __init__(self, key: Optional[str]) -> None: 
            self.key = key
            super().__init__()

    def on_mount(self) -> None:
        self.add_columns("Title", "Artist", "Album")
        self.cursor_type = "row"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        if event.row_key.value:
            self.post_message(self.RowSelected(event.row_key.value))

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        self.post_message(self.RowHighlighted(event.row_key.value))

    def update_results(self, results: List[SearchResult]) -> None:
        self.clear()
        for r in results:
            self.add_row(r.title, r.artist, r.album_name, key=r.video_id)
        self.focus()


class LogPane(RichLog):
    """A dedicated widget for logging application events."""
    def add_message(self, message: str) -> None:
        self.write(message)