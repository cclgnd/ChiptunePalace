import sys
import os
import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QWidget,
                               QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QTabWidget, QMenu, QLineEdit,
                               QSplitter, QListWidgetItem, QProgressBar,
                               QTreeView, QTableWidget, QTableWidgetItem,
                               QHeaderView, QSlider, QFrame, QAbstractItemView,
                               QFileSystemModel, QTreeWidget, QTreeWidgetItem)
from PySide6.QtGui import QPainter, QColor, QFont, QAction, QIcon, QPixmap
from PySide6.QtCore import Qt, QSize, QTimer, QUrl, QDir, Signal, QThread

from chiptunepalace.services.audio_engine import AudioEngine, PlaybackState
from chiptunepalace.services.web_scraper_service import WebScraperService, ScraperThread
from chiptunepalace.services.queue_manager import QueueManager
from chiptunepalace.services.track_service import TrackService
from chiptunepalace.services.hotkey_service import HotkeyService
from chiptunepalace.services.download_service import DownloadService
from chiptunepalace.gui.theme import GLOBAL_STYLE, C_ACCENT, C_BG, FONT_PIXEL, C_LIME, C_CYAN, C_BORDER, C_MUTED

# ── Scanline Overlay ─────────────────────────────────────────────────
class ScanlineOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setObjectName("scanlineOverlay")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(Qt.NoPen)
        color = QColor(0, 0, 0, 20)
        for y in range(0, self.height(), 4):
            p.fillRect(0, y, self.width(), 2, color)

# ── Pixel Visualizer ─────────────────────────────────────────────────
class PixelVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(160, 40))
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.is_playing = False
        self.bars = [2] * 8

    def start(self):
        self.is_playing = True
        self.timer.start(80)

    def stop(self):
        self.is_playing = False
        self.timer.stop()
        self.update()

    def paintEvent(self, event):
        import random
        p = QPainter(self)
        if self.is_playing:
            self.bars = [random.randint(4, 30) for _ in self.bars]
        else:
            self.bars = [2] * 8
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C_ACCENT))
        for i, h in enumerate(self.bars):
            p.drawRect(i * 20 + 2, 40 - h, 14, h)

# ── Job Item Widget ──────────────────────────────────────────────────
class JobItemWidget(QWidget):
    cancel_requested = Signal(str)

    def __init__(self, job_id, name, parent=None):
        super().__init__(parent)
        self.job_id = job_id
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        
        self.label = QLabel(f"[{job_id}] {name}")
        self.label.setStyleSheet("font-size: 10px;")
        layout.addWidget(self.label, stretch=1)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setFixedHeight(12)
        layout.addWidget(self.progress, stretch=1)
        
        self.btn_cancel = QPushButton("X")
        self.btn_cancel.setFixedSize(20, 20)
        self.btn_cancel.clicked.connect(lambda: self.cancel_requested.emit(self.job_id))
        layout.addWidget(self.btn_cancel)

    def set_progress(self, pct):
        self.progress.setValue(pct)

    def set_status(self, status):
        self.label.setText(f"[{self.job_id}] {status}")

# ── Artwork Thread ───────────────────────────────────────────────────
class ArtThread(QThread):
    finished = Signal(dict)

    def __init__(self, scraper, console, game):
        super().__init__()
        self.scraper = scraper
        self.console = console
        self.game = game

    def run(self):
        urls = self.scraper.get_artwork(self.console, self.game)
        results = {}
        for key, url in urls.items():
            try:
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    results[key] = resp.content
            except:
                pass
        self.finished.emit(results)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Services
        self.track_service    = TrackService()
        self.audio_engine     = AudioEngine()
        self.scraper_service  = WebScraperService()
        self.queue_manager    = QueueManager(self.track_service, self.audio_engine)
        self.hotkey_service   = HotkeyService(self.audio_engine, self.queue_manager)
        self.download_service = DownloadService(download_dir='chiptunepalace/downloads')

        self._jobs = {}
        self._current_search_thread = None

        # Signals
        self.audio_engine.playback_state_changed.connect(self._on_state_change)
        self.audio_engine.position_changed.connect(self._update_playback_slider)
        self.audio_engine.duration_changed.connect(self._update_playback_duration)
        self.audio_engine.error_occurred.connect(self._on_audio_error)

        self._build_ui()
        self._load_local_files()
        self._load_consoles()

    def _build_ui(self):
        self.setWindowTitle("CHIPTUNEPALACE // TETRIS EDITION")
        self.resize(1200, 850)
        self.setStyleSheet(GLOBAL_STYLE)

        self.central_widget = QWidget()
        self.central_widget.setObjectName("centralWidget")
        self.setCentralWidget(self.central_widget)
        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header ──
        header = QFrame()
        header.setFixedHeight(80)
        header_layout = QHBoxLayout(header)
        
        title = QLabel("CHIPTUNE PALACE")
        title.setProperty("class", "titleLabel")
        header_layout.addWidget(title)
        
        self.visualizer = PixelVisualizer()
        header_layout.addWidget(self.visualizer)
        
        header_layout.addStretch()
        
        search_box = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("SEARCH WEB (e.g. Sonic, Mario)...")
        self.search_input.setFixedWidth(300)
        self.search_input.returnPressed.connect(self._perform_search)
        search_box.addWidget(self.search_input)
        
        btn_search = QPushButton("SEARCH")
        btn_search.clicked.connect(self._perform_search)
        search_box.addWidget(btn_search)
        header_layout.addLayout(search_box)
        
        main_layout.addWidget(header)

        # ── Middle Splitter ──
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Sidebar
        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(280)
        sidebar_layout = QVBoxLayout(self.sidebar)
        
        # Sidebar Tabs
        self.side_tabs = QTabWidget()
        
        # Tab: Library (Folders)
        folder_w = QWidget()
        folder_l = QVBoxLayout(folder_w)
        self.folder_view = QTreeView()
        self.folder_model = QFileSystemModel()
        self.folder_model.setRootPath(QDir.currentPath())
        self.folder_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)
        self.folder_model.setNameFilters(['*.vgm', '*.vgz', '*.spc', '*.nsf', '*.sid', '*.mod', '*.s3m', '*.xm', '*.it'])
        self.folder_model.setNameFilterDisables(False)
        self.folder_view.setModel(self.folder_model)
        self.folder_view.setRootIndex(self.folder_model.index(QDir.currentPath()))
        self.folder_view.hideColumn(1) # Size
        self.folder_view.hideColumn(2) # Type
        self.folder_view.hideColumn(3) # Date
        self.folder_view.doubleClicked.connect(self._on_folder_item_dblclick)
        folder_l.addWidget(self.folder_view)
        self.side_tabs.addTab(folder_w, "FOLDERS")
        
        # Tab: Catalog (Consoles)
        catalog_w = QWidget()
        catalog_l = QVBoxLayout(catalog_w)
        self.catalog_tree = QTreeWidget()
        self.catalog_tree.setHeaderHidden(True)
        self.catalog_tree.itemExpanded.connect(self._on_catalog_item_expanded)
        self.catalog_tree.itemSelectionChanged.connect(self._on_catalog_selection_changed)
        self.catalog_tree.itemDoubleClicked.connect(self._on_catalog_dblclick)
        catalog_l.addWidget(self.catalog_tree)
        self.side_tabs.addTab(catalog_w, "CATALOG")
        
        sidebar_layout.addWidget(self.side_tabs)
        
        # Jobs Panel (Bottom of sidebar)
        jobs_label = QLabel("ACTIVE JOBS")
        jobs_label.setStyleSheet(f"color: {C_ACCENT}; font-weight: bold; margin-top: 10px;")
        sidebar_layout.addWidget(jobs_label)
        self.jobs_list = QListWidget()
        self.jobs_list.setFixedHeight(150)
        sidebar_layout.addWidget(self.jobs_list)
        
        self.splitter.addWidget(self.sidebar)
        
        # Main Area
        self.main_content = QWidget()
        self.main_content.setObjectName("mainContent")
        main_content_layout = QVBoxLayout(self.main_content)
        
        # Track Table
        self.track_table = QTableWidget(0, 5)
        self.track_table.setHorizontalHeaderLabels(["FILENAME", "ARTIST", "SYSTEM", "LENGTH", "SOURCE"])
        self.track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.track_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.track_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.track_table.itemDoubleClicked.connect(self._on_track_dblclick)
        main_content_layout.addWidget(self.track_table)
        
        # Online Results List (Overlay/Tab?)
        self.results_list = QListWidget()
        self.results_list.hide() # Show only when searching
        self.results_list.itemDoubleClicked.connect(self._on_search_result_dblclick)
        main_content_layout.addWidget(self.results_list)
        
        self.splitter.addWidget(self.main_content)
        
        # ── Artwork Sidebar ──
        self.art_panel = QWidget()
        self.art_panel.setObjectName("artPanel")
        self.art_panel.setFixedWidth(250)
        art_layout = QVBoxLayout(self.art_panel)
        
        self.art_label = QLabel("BOX ART")
        self.art_label.setAlignment(Qt.AlignCenter)
        self.art_label.setFixedSize(220, 220)
        self.art_label.setStyleSheet(f"border: 2px solid {C_BORDER}; background: #000;")
        art_layout.addWidget(self.art_label)
        
        self.snap_label = QLabel("SCREENSHOT")
        self.snap_label.setAlignment(Qt.AlignCenter)
        self.snap_label.setFixedSize(220, 160)
        self.snap_label.setStyleSheet(f"border: 2px solid {C_BORDER}; background: #000;")
        art_layout.addWidget(self.snap_label)
        
        self.desc_label = QLabel("GAME INFO")
        self.desc_label.setWordWrap(True)
        self.desc_label.setStyleSheet(f"color: {C_MUTED}; font-size: 10px;")
        art_layout.addWidget(self.desc_label)
        
        art_layout.addStretch()
        
        self.splitter.addWidget(self.art_panel)
        
        main_layout.addWidget(self.splitter, stretch=1)

        # ── Playback Bar ──
        playback_bar = QFrame()
        playback_bar.setObjectName("playbackBar")
        playback_bar.setFixedHeight(100)
        pb_layout = QVBoxLayout(playback_bar)
        
        # Seek row
        seek_layout = QHBoxLayout()
        self.time_label = QLabel("00:00")
        self.playback_slider = QSlider(Qt.Horizontal)
        self.playback_slider.setRange(0, 1000)
        self.playback_slider.sliderMoved.connect(self._on_seek)
        self.duration_label = QLabel("00:00")
        seek_layout.addWidget(self.time_label)
        seek_layout.addWidget(self.playback_slider)
        seek_layout.addWidget(self.duration_label)
        pb_layout.addLayout(seek_layout)
        
        # Controls row
        ctrl_layout = QHBoxLayout()
        
        # Now playing info
        self.np_info = QLabel("SYSTEM READY // IDLE")
        self.np_info.setProperty("class", "nowPlayingLabel")
        self.np_info.setFixedWidth(300)
        ctrl_layout.addWidget(self.np_info)
        
        ctrl_layout.addStretch()
        
        self.btn_prev = QPushButton("⏮")
        self.btn_prev.clicked.connect(self.queue_manager.previous_track)
        self.btn_play = QPushButton("▶")
        self.btn_play.setObjectName("playBtn")
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_next = QPushButton("⏭")
        self.btn_next.clicked.connect(self.queue_manager.advance_to_next_track)
        
        ctrl_layout.addWidget(self.btn_prev)
        ctrl_layout.addWidget(self.btn_play)
        ctrl_layout.addWidget(self.btn_next)
        
        ctrl_layout.addStretch()
        
        # Volume
        vol_label = QLabel("VOL")
        self.vol_slider = QSlider(Qt.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(80)
        self.vol_slider.setFixedWidth(100)
        self.vol_slider.valueChanged.connect(self.audio_engine.set_volume)
        ctrl_layout.addWidget(vol_label)
        ctrl_layout.addWidget(self.vol_slider)
        
        pb_layout.addLayout(ctrl_layout)
        main_layout.addWidget(playback_bar)

        # Scanline Overlay
        self.scanline = ScanlineOverlay(self.central_widget)
        self.scanline.resize(self.size())

    def resizeEvent(self, event):
        self.scanline.resize(self.size())
        super().resizeEvent(event)

    # ── Logic ──

    def _load_local_files(self):
        """Refreshes the track table with local tracks from DB."""
        tracks = self.track_service.get_all_tracks()
        self.track_table.setRowCount(0)
        for t in tracks:
            row = self.track_table.rowCount()
            self.track_table.insertRow(row)
            
            fpath = t.get('file_path', '')
            fname = os.path.basename(fpath)
            
            item_name = QTableWidgetItem(fname)
            item_name.setData(Qt.UserRole, t['track_id'])
            
            self.track_table.setItem(row, 0, item_name)
            self.track_table.setItem(row, 1, QTableWidgetItem(t.get('artist', 'Unknown')))
            self.track_table.setItem(row, 2, QTableWidgetItem(t.get('genre', 'Chiptune')))
            self.track_table.setItem(row, 3, QTableWidgetItem("--:--"))
            self.track_table.setItem(row, 4, QTableWidgetItem("LOCAL"))
            
        track_ids = [t['track_id'] for t in tracks]
        self.queue_manager.load_playlist(track_ids)
        # Refresh catalog to update [LOCAL] tags
        self._load_consoles()

    def _load_consoles(self):
        self.np_info.setText("FETCHING CONSOLES...")
        self.catalog_tree.clear()
        self.console_thread = ScraperThread(self.scraper_service.get_consoles)
        self.console_thread.finished.connect(self._on_consoles_loaded)
        self.console_thread.start()

    def _on_consoles_loaded(self, consoles):
        for c in consoles:
            it = QTreeWidgetItem(self.catalog_tree)
            it.setText(0, c['name'].upper())
            it.setData(0, Qt.UserRole, {"type": "console", "url": c['url']})
            # Add dummy child to show expansion arrow
            QTreeWidgetItem(it) 
        self.np_info.setText("READY")

    def _on_catalog_item_expanded(self, item):
        data = item.data(0, Qt.UserRole)
        if not data: return
        
        # Clear dummy
        if item.childCount() == 1 and not item.child(0).data(0, Qt.UserRole):
            item.removeChild(item.child(0))
            
            if data['type'] == "console":
                self._expand_console(item, data['url'])
            elif data['type'] == "game":
                self._expand_game(item, data['url'])

    def _expand_console(self, item, url):
        self.np_info.setText(f"LOADING PACKS...")
        thread = ScraperThread(self.scraper_service.get_packs_by_console, url)
        thread.finished.connect(lambda p: self._on_packs_loaded(item, p))
        thread.start()
        # Prevent GC
        item._thread = thread

    def _on_packs_loaded(self, parent_item, packs):
        local_albums = [t['album'] for t in self.track_service.get_all_tracks()]
        for p in packs:
            name = p['title']
            is_local = name in local_albums
            display_name = f"{name} [LOCAL]" if is_local else name
            
            it = QTreeWidgetItem(parent_item)
            it.setText(0, display_name)
            if is_local:
                it.setForeground(0, QColor("#00FF00")) # LIME
            
            it.setData(0, Qt.UserRole, {"type": "game", "url": p['url'], "title": name})
            # Add dummy
            QTreeWidgetItem(it)
        self.np_info.setText("READY")

    def _expand_game(self, item, url):
        self.np_info.setText(f"LOADING TRACKS...")
        thread = ScraperThread(self.scraper_service.get_tracks_in_pack, url)
        thread.finished.connect(lambda t: self._on_tracks_loaded(item, t))
        thread.start()
        item._thread = thread

    def _on_tracks_loaded(self, parent_item, tracks):
        for t in tracks:
            it = QTreeWidgetItem(parent_item)
            it.setText(0, t['title'])
            it.setData(0, Qt.UserRole, {"type": "track", "title": t['title']})
        self.np_info.setText("READY")

    def _on_catalog_dblclick(self, item, column):
        data = item.data(0, Qt.UserRole)
        if not data: return
        
        if data['type'] == "game":
            # Start download/stream
            self._on_search_result_dblclick(None, data) # reuse logic
        elif data['type'] == "track":
            # If parent is local, find and play local file?
            # For now, just trigger game download
            parent = item.parent()
            if parent:
                self._on_catalog_dblclick(parent, 0)
        self.np_info.setText("READY")

    def _on_catalog_selection_changed(self):
        item = self.catalog_tree.currentItem()
        if not item: return
        data = item.data(0, Qt.UserRole)
        if not data or data.get('type') != 'game': return
        
        console_item = item.parent()
        if not console_item: return
        console_name = console_item.text(0)
        game_name = data['title']
        
        self.desc_label.setText(f"LOADING ARTWORK FOR {game_name}...")
        self._art_thread = ArtThread(self.scraper_service, console_name, game_name)
        self._art_thread.finished.connect(self._on_art_loaded)
        self._art_thread.start()

    def _on_art_loaded(self, results):
        if 'boxart' in results:
            pix = QPixmap()
            pix.loadFromData(results['boxart'])
            self.art_label.setPixmap(pix.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.art_label.setText("NO BOXART")

        if 'screenshot' in results:
            pix = QPixmap()
            pix.loadFromData(results['screenshot'])
            self.snap_label.setPixmap(pix.scaled(220, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.snap_label.setText("NO SCREENSHOT")
            
        self.desc_label.setText("Extracted from Libretro repositories.")

    def _perform_search(self):
        q = self.search_input.text().strip()
        if not q: return
        self.np_info.setText(f"SEARCHING: {q.upper()}...")
        
        if self._current_search_thread:
            self._current_search_thread.terminate()
            
        self._current_search_thread = ScraperThread(self.scraper_service.search_online, q)
        self._current_search_thread.finished.connect(self._on_search_finished)
        self._current_search_thread.start()

    def _on_search_finished(self, results):
        self.results_list.clear()
        for r in results:
            it = QListWidgetItem(f"[{r['source']}] {r['title']}")
            it.setData(Qt.UserRole, r['url'])
            self.results_list.addItem(it)
        self.results_list.show()
        self.track_table.hide()
        self.np_info.setText(f"RESULTS: {len(results)}")

    def _on_search_result_dblclick(self, item, data=None):
        if data:
            url = data['url']
            name = data['title']
        else:
            url = item.data(Qt.UserRole)
            name = item.text()
            
        self.np_info.setText(f"DOWNLOADING {name}...")
        
        job_id = self.download_service.download_pack(
            url, name,
            on_finished=self._on_download_done,
            on_progress=self._on_download_progress,
            on_status=self._on_download_status
        )
        
        # Custom job widget
        widget = JobItemWidget(job_id, name)
        widget.cancel_requested.connect(self.download_service.cancel_job)
        
        list_item = QListWidgetItem(self.jobs_list)
        list_item.setSizeHint(widget.sizeHint())
        self.jobs_list.addItem(list_item)
        self.jobs_list.setItemWidget(list_item, widget)
        
        self._jobs[job_id] = {"widget": widget, "name": name, "list_item": list_item}

    def _on_download_progress(self, job_id, pct):
        if job_id in self._jobs:
            self._jobs[job_id]["widget"].set_progress(pct)

    def _on_download_status(self, job_id, status):
        if job_id in self._jobs:
            self._jobs[job_id]["widget"].set_status(status)
            if "CANCELLED" in status or "FAILED" in status:
                 # Remove after a delay?
                 QTimer.singleShot(2000, lambda: self._remove_job(job_id))

    def _remove_job(self, job_id):
        if job_id in self._jobs:
            row = self.jobs_list.row(self._jobs[job_id]["list_item"])
            self.jobs_list.takeItem(row)
            del self._jobs[job_id]

    def _on_download_done(self, folder_path, job_id):
        self._load_local_files() # Refresh table
        self.results_list.hide()
        self.track_table.show()
        self.np_info.setText("DOWNLOAD COMPLETE")

    def _on_folder_item_dblclick(self, index):
        path = self.folder_model.filePath(index)
        if not os.path.isdir(path):
            # Play file directly if it's a track
            ext = os.path.splitext(path)[1].lower()
            if ext in ['.vgm', '.vgz', '.spc', '.nsf', '.sid', '.mod', '.s3m', '.xm', '.it']:
                # For direct play, we might want to add it to a temporary queue or DB
                self.audio_engine.load_track(path)
                self.audio_engine.play()

    def _on_track_dblclick(self, item):
        tid = item.data(Qt.UserRole)
        if tid:
            self.queue_manager.start_playback(tid)

    def _toggle_play(self):
        if self.audio_engine.state == PlaybackState.PLAYING:
            self.audio_engine.pause()
        elif self.audio_engine.state == PlaybackState.PAUSED:
            self.audio_engine.play()
        else:
            self.queue_manager.advance_to_next_track()

    def _on_state_change(self, state):
        if state == PlaybackState.PLAYING:
            self.btn_play.setText("⏸")
            self.visualizer.start()
            tid = self.queue_manager.get_current_track_id()
            if tid:
                t = self.track_service.get_track_by_id(tid)
                self.np_info.setText(f"NOW PLAYING: {os.path.basename(t['file_path']).upper()}")
        else:
            self.btn_play.setText("▶")
            self.visualizer.stop()

    def _update_playback_slider(self, seconds):
        if not self.playback_slider.isSliderDown():
            self.time_label.setText(self._format_time(seconds))
            if self.audio_engine.player:
                duration = self.audio_engine.player.get_length() / 1000.0
                if duration > 0:
                    val = int((seconds / duration) * 1000)
                    self.playback_slider.setValue(val)

    def _update_playback_duration(self, seconds):
        self.duration_label.setText(self._format_time(seconds))

    def _on_seek(self, value):
        if self.audio_engine.player:
            duration = self.audio_engine.player.get_length() / 1000.0
            if duration > 0:
                pos = (value / 1000.0) * duration
                self.audio_engine.set_time(pos)

    def _format_time(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}:{s:02d}"

    def _on_audio_error(self, msg):
        self.np_info.setText(f"ERROR: {msg[:30]}")

    def closeEvent(self, event):
        self.hotkey_service.cleanup()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
