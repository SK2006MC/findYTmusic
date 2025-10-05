# findYTmusic-tui

A thoughtful, terminal-based user interface for searching and downloading music from YouTube Music.

This tool is designed for those who appreciate the power and elegance of the command line. It provides a clean, fast, and keyboard-driven environment to discover music and seamlessly acquire it through your favorite command-line downloader.

![Screen shot](./s1 "Screen shot")
![Screen shot2](./s2 "Screen shot2")

## ✨ Features

*   **Interactive TUI**: A clean, two-pane interface built with the modern [Textual](https://github.com/Textualize/textual) framework.
*   **Real-time Search**: Instantly search YouTube Music as you type.
*   **Detailed View**: Select a song to see all available details, including artist, album, and whether it's explicit.
*   **Seamless Downloader Integration**: Press `Enter` on a song to download it using an external tool like `gytmdl` or `yt-dlp`.
*   **Copy to Clipboard**: Press `c` to instantly copy a song's YouTube Music link.
*   **Persistent Log**: A clear, scrollable log of all actions, from searches to successful (or failed) downloads.
*   **Keyboard-Driven**: Designed for efficient, mouse-free operation.

## 🚀 Installation

This tool is built with Python and requires a few external dependencies to function fully.

### Prerequisites

1.  **Python**: A modern version of Python (3.9 or newer) is recommended.
2.  **A Downloader**: The tool is designed to call an external downloader.
    *   **`gytmdl`** (Recommended): A feature-rich downloader specifically for YouTube Music. Install with `pip install gytmdl`.
3.  **FFmpeg**: Your chosen downloader will almost certainly require FFmpeg for audio processing. Ensure it is installed and available in your system's PATH.
4.  **Clipboard Tool** (Optional): To enable the copy-to-clipboard feature, the `pyperclip` library is used.

### Setup
1.  ```
    git clone https://github.com/SK2006MC/findYTmusic-tui
    ```

2.  **Create a Virtual Environment** (Highly Recommended)
    This isolates the project's dependencies from your system's Python.
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install Python Dependencies**
    ```bash
    pip install "textual[dev]" ytmusicapi pyperclip
    ```

## 🔧 Usage

With your virtual environment activated, simply run the script:

```bash
python find_ytmusic_tui.py
```

### Controls

| Key(s)               | Action                                 |
| -------------------- | -------------------------------------- |
| `(type in input)`    | Enter search terms                     |
| `Enter` (in input)   | Execute search                         |
| `Up`/`Down` Arrows   | Navigate the results list              |
| `Enter` (on result)  | Download the selected song             |
| `c`                  | Copy the selected song's link          |
| `d`                  | Toggle between light and dark mode     |
| `q` or `Ctrl+C`      | Quit the application                   |

## ⚙️ Configuration

The application's behavior can be easily adjusted by modifying the `Config` class at the top of the `find_ytmusic_tui.py` script.

```python
@dataclass
class Config:
    """Holds all application configuration."""
    SEARCH_RESULT_LIMIT: int = 25
    DOWNLOAD_COMMAND: str = "gytmdl"
```

*   `SEARCH_RESULT_LIMIT`: Change the number of results to fetch per search.
*   `DOWNLOAD_COMMAND`: Change this to your preferred downloader, for example: `"yt-dlp"`. The tool will automatically detect if the command exists in your PATH.

## 🛠️ Built With

*   **[Textual](https://github.com/Textualize/textual)**: A modern TUI (Text User Interface) framework for Python.
*   **[ytmusicapi](https://github.com/sigma67/ytmusicapi)**: An unofficial API for YouTube Music.
*   **[Rich](https://github.com/Textualize/rich)**: The powerful library that provides beautiful formatting in the terminal for Textual.

## 📄 License

This project is licensed under the GPLv3 License. See the LICENSE file for details.
