"""
theme.py — Chiptune Palace Global Theme
Tetris Classic Palace aesthetic: deep navy/indigo bricks, hot-pink accents,
electric-lime highlights, phosphor-green text, CRT scanline feel.
"""

# ── Palette ──────────────────────────────────────────────────────────────────
C_BG            = "rgba(13, 13, 26, 230)"   # Semi-transparent navy
C_BRICK1        = "rgba(22, 33, 62, 180)"   # Translucent dark blue
C_BRICK2        = "rgba(15, 52, 96, 200)"   # Translucent deeper blue
C_ACCENT        = "#e94560"   # Hot-pink — primary CTA, selected items
C_ACCENT2       = "#ff6b6b"   # Coral-pink — hover tint
C_LIME          = "#39ff14"   # Electric lime — track name text / "lit" indicator
C_GREEN         = "#00ff41"   # Phosphor green — library text
C_CYAN          = "#00d4ff"   # Neon cyan — playback position / progress chunk
C_YELLOW        = "#ffd700"   # Gold — starred / volume icon
C_TEXT          = "#e8e8e8"   # Off-white — general labels
C_MUTED         = "#6a7080"   # Muted blue-grey — disabled / placeholder
C_BORDER        = "#2a2a4a"   # Subtle border separators
C_SCROLLBAR     = "#1e1e3a"   # Scrollbar track

# ── Typography ───────────────────────────────────────────────────────────────
FONT_PIXEL  = "Courier New"    # Monospace pixel feel (always available)
FONT_TITLE  = "Courier New"    # Title / headings

# ── Sizes ────────────────────────────────────────────────────────────────────
BORDER_RADIUS = "4px"
BTN_PADDING   = "6px 14px"
INPUT_PADDING = "6px 10px"

# ── Global QSS ───────────────────────────────────────────────────────────────
GLOBAL_STYLE = f"""
/* === Base === */
QMainWindow, QDialog {{
    background-color: {C_BG};
}}
QWidget {{
    background-color: {C_BG};
    color: {C_TEXT};
    font-family: '{FONT_PIXEL}';
    font-size: 12px;
}}

/* === Labels === */
QLabel {{
    color: {C_TEXT};
    font-family: '{FONT_PIXEL}';
}}

/* === LineEdit / Search === */
QLineEdit {{
    background-color: {C_BRICK2};
    color: {C_GREEN};
    border: 2px solid {C_ACCENT};
    border-radius: {BORDER_RADIUS};
    padding: {INPUT_PADDING};
    font-family: '{FONT_PIXEL}';
    selection-background-color: {C_ACCENT};
}}
QLineEdit:focus {{
    border-color: {C_CYAN};
    color: {C_LIME};
}}
QLineEdit::placeholder {{
    color: {C_MUTED};
}}

/* === Buttons === */
QPushButton {{
    background-color: {C_BRICK2};
    color: {C_TEXT};
    border: 2px solid {C_ACCENT};
    border-radius: {BORDER_RADIUS};
    padding: {BTN_PADDING};
    font-family: '{FONT_PIXEL}';
    font-weight: bold;
    letter-spacing: 1px;
}}
QPushButton:hover {{
    background-color: {C_ACCENT};
    color: #ffffff;
    border-color: {C_ACCENT2};
}}
QPushButton:pressed {{
    background-color: #a82d43;
    border-color: {C_ACCENT};
}}
QPushButton:checked {{
    background-color: {C_ACCENT};
    color: #ffffff;
    border-color: {C_LIME};
}}
QPushButton:disabled {{
    color: {C_MUTED};
    border-color: {C_BORDER};
    background-color: {C_BRICK1};
}}

/* === Tool Buttons (transport icon buttons) === */
QToolButton {{
    background-color: {C_BRICK2};
    color: {C_TEXT};
    border: 2px solid {C_ACCENT};
    border-radius: {BORDER_RADIUS};
    padding: 6px;
    font-family: '{FONT_PIXEL}';
    font-weight: bold;
}}
QToolButton:hover {{ background-color: {C_ACCENT}; }}
QToolButton:checked {{ background-color: {C_ACCENT}; border-color: {C_LIME}; }}

/* === Sliders === */
QSlider::groove:horizontal {{
    height: 6px;
    background: {C_BRICK2};
    border: 1px solid {C_BORDER};
    border-radius: 3px;
}}
QSlider::sub-page:horizontal {{
    background: {C_CYAN};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {C_ACCENT};
    border: 2px solid {C_ACCENT2};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{
    background: {C_ACCENT2};
}}

/* === Progress Bars === */
QProgressBar {{
    background: {C_BRICK2};
    border: 1px solid {C_ACCENT};
    border-radius: {BORDER_RADIUS};
    color: {C_TEXT};
    text-align: center;
    font-family: '{FONT_PIXEL}';
    font-size: 11px;
    height: 18px;
}}
QProgressBar::chunk {{
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:0,
        stop:0 {C_ACCENT}, stop:1 {C_CYAN}
    );
    border-radius: 3px;
}}

/* === List Widgets === */
QListWidget {{
    background-color: {C_BRICK1};
    color: {C_GREEN};
    border: 1px solid {C_BORDER};
    border-radius: {BORDER_RADIUS};
    font-family: '{FONT_PIXEL}';
    font-size: 12px;
    outline: none;
}}
QListWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {C_BORDER};
}}
QListWidget::item:selected {{
    background-color: {C_ACCENT};
    color: #ffffff;
}}
QListWidget::item:hover {{
    background-color: {C_BRICK2};
    color: {C_LIME};
}}

/* === Tree Widget (folder browser) === */
QTreeWidget {{
    background-color: {C_BRICK1};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    border-radius: {BORDER_RADIUS};
    font-family: '{FONT_PIXEL}';
    font-size: 12px;
    outline: none;
}}
QTreeWidget::item {{
    padding: 3px 4px;
}}
QTreeWidget::item:selected {{
    background-color: {C_ACCENT};
    color: #ffffff;
}}
QTreeWidget::item:hover {{
    background-color: {C_BRICK2};
    color: {C_LIME};
}}
QTreeWidget QHeaderView::section {{
    background-color: {C_BRICK2};
    color: {C_ACCENT};
    border: 1px solid {C_BORDER};
    padding: 4px;
    font-family: '{FONT_PIXEL}';
    font-weight: bold;
}}

/* === Table Widget === */
QTableWidget {{
    background-color: {C_BRICK1};
    color: {C_TEXT};
    border: 1px solid {C_BORDER};
    gridline-color: {C_BORDER};
    font-family: '{FONT_PIXEL}';
    font-size: 11px;
    outline: none;
    selection-background-color: {C_ACCENT};
}}
QTableWidget::item {{
    padding: 3px 6px;
}}
QTableWidget::item:selected {{
    background-color: {C_ACCENT};
    color: #ffffff;
}}
QTableWidget::item:hover {{
    background-color: {C_BRICK2};
    color: {C_LIME};
}}
QHeaderView::section {{
    background-color: {C_BRICK2};
    color: {C_ACCENT};
    border: 1px solid {C_BORDER};
    padding: 5px;
    font-family: '{FONT_PIXEL}';
    font-weight: bold;
    font-size: 11px;
}}

/* === Tabs === */
QTabWidget::pane {{
    border: 1px solid {C_ACCENT};
    background: {C_BG};
    border-radius: 0px;
}}
QTabBar {{
    background: transparent;
}}
QTabBar::tab {{
    background: {C_BRICK2};
    color: {C_TEXT};
    padding: 8px 16px;
    border: 1px solid {C_BORDER};
    border-bottom: none;
    font-family: '{FONT_PIXEL}';
    font-weight: bold;
    letter-spacing: 1px;
}}
QTabBar::tab:selected {{
    background: {C_ACCENT};
    color: #ffffff;
    border-color: {C_ACCENT};
}}
QTabBar::tab:hover:!selected {{
    background: {C_BRICK1};
    color: {C_LIME};
    border-color: {C_ACCENT2};
}}

/* === Splitter === */
QSplitter::handle {{
    background: {C_ACCENT};
    width: 2px;
    height: 2px;
}}

/* === Scrollbars === */
QScrollBar:vertical {{
    background: {C_SCROLLBAR};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {C_ACCENT};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C_ACCENT2};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: {C_SCROLLBAR};
    height: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:horizontal {{
    background: {C_ACCENT};
    border-radius: 5px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* === Combo Box === */
QComboBox {{
    background-color: {C_BRICK2};
    color: {C_GREEN};
    border: 2px solid {C_ACCENT};
    border-radius: {BORDER_RADIUS};
    padding: {INPUT_PADDING};
    font-family: '{FONT_PIXEL}';
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox::down-arrow {{
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 8px solid {C_ACCENT};
    width: 0; height: 0;
}}
QComboBox QAbstractItemView {{
    background-color: {C_BRICK1};
    color: {C_TEXT};
    border: 1px solid {C_ACCENT};
    selection-background-color: {C_ACCENT};
}}

/* === Spin Box === */
QSpinBox {{
    background-color: {C_BRICK2};
    color: {C_GREEN};
    border: 2px solid {C_ACCENT};
    border-radius: {BORDER_RADIUS};
    padding: {INPUT_PADDING};
    font-family: '{FONT_PIXEL}';
}}

/* === Menu === */
QMenu {{
    background-color: {C_BRICK1};
    color: {C_TEXT};
    border: 1px solid {C_ACCENT};
    font-family: '{FONT_PIXEL}';
}}
QMenu::item:selected {{
    background-color: {C_ACCENT};
    color: #ffffff;
}}
QMenu::separator {{
    height: 1px;
    background: {C_BORDER};
    margin: 4px 0;
}}

/* === Status Bar === */
QStatusBar {{
    background-color: {C_BRICK2};
    color: {C_MUTED};
    border-top: 1px solid {C_BORDER};
    font-family: '{FONT_PIXEL}';
    font-size: 11px;
}}

/* === Group Box === */
QGroupBox {{
    border: 1px solid {C_ACCENT};
    border-radius: {BORDER_RADIUS};
    margin-top: 14px;
    color: {C_ACCENT};
    font-family: '{FONT_PIXEL}';
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {C_ACCENT};
}}

/* === Tooltip === */
QToolTip {{
    background-color: {C_BRICK1};
    color: {C_LIME};
    border: 1px solid {C_ACCENT};
    padding: 4px;
    font-family: '{FONT_PIXEL}';
}}
"""
