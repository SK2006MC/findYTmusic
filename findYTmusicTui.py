Screen {
    layout: vertical;
    background: $surface;
    color: $text;
}

#main-container {
    height: 1fr;
    padding: 1 2;
}

#app-grid {
    height: 1fr;
    grid-size: 2;
    grid-gutter: 1 2;
}

#left-pane {
    width: 60%;
}

#right-pane {
    width: 40%;
}

#search-input {
    margin-bottom: 1;
}

#results-table {
    border: round $primary;
    height: 1fr;
}

#details-pane {
    border: round $secondary;
    padding: 0 1;
    height: 1fr;
}

#log {
    background: $panel;
    border: heavy $background;
    height: 5;
    dock: bottom;
    margin: 1 0 0 0;
}