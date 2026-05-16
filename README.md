# Chiptune Palace

A high-fidelity, standalone retro music repository manager and player. Built with PySide6 and themed after the classic "Tetris Palace" aesthetic.

![Chiptune Palace Icon](icon.png)

## Features
- **3-Tier Catalog:** Browse music by Console -> Game -> Track.
- **ZIP Streaming:** Stream individual tracks directly from online ZIP archives without full extraction.
- **Live Artwork:** Automatic fetching of high-quality Box Art and Gameplay Screenshots via Libretro Thumbnails.
- **Local Library Tracking:** Identifies tracks you already have with green `[LOCAL]` tags.
- **Premium UI:** Frameless window with custom controls and semi-transparent background.
- **Global Hotkeys:** Control playback from anywhere (Media keys supported).
- **Portable:** Bundled as a standalone `.exe` for easy distribution.

## Installation (Development)
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python launcher.pyw
   ```

## Bundling as EXE
To build the standalone executable:
```bash
python -m PyInstaller --noconsole --onefile --icon=icon.png --add-data "icon.png;." --name="ChiptunePalace" launcher.pyw
```

## Technologies
- **Python 3.14+**
- **PySide6** (GUI)
- **SQLAlchemy** (Database)
- **python-vlc** (Audio Engine)
- **BeautifulSoup4** (Web Scraping)
- **Pillow** (Icon processing)
