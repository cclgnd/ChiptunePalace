import sys
import os
import requests
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QWidget,
                               QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QTabWidget, QMenu, QLineEdit,
                               QSplitter, QListWidgetItem, QProgressBar,
                               QTreeWidget, QTreeWidgetItem, QFileDialog,
                               QGroupBox, QFormLayout, QSplitter)
from PySide6.QtGui import QPainter, QColor, QFont, QAction, QMouseEvent, QIcon, QPixmap
from PySide6.QtCore import Qt, QSize, QTimer, QPoint, QThread, Signal
from chiptunepalace.services.audio_engine import AudioEngine, PlaybackState
from chiptunepalace.services.web_scraper_service import WebScraperService, ScraperThread
from chiptunepalace.services.queue_manager import QueueManager
from chiptunepalace.services.track_service import TrackService
from chiptunepalace.services.hotkey_service import HotkeyService
from chiptunepalace.services.download_service import DownloadService
from chiptunepalace.services.config_service import ConfigService

from chiptunepalace.gui.theme import GLOBAL_STYLE, C_ACCENT, C_BG, FONT_PIXEL, C_LIME, C_CYAN


# ── Pixel Visualizer ─────────────────────────────────────────────────
class PixelVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(QSize(200, 50))
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.is_playing = False
        self.bars = [2] * 10

    def start(self):
        self.is_playing = True
        self.timer.start(100)

    def stop(self):
        self.is_playing = False
        self.timer.stop()
        self.update()

    def paintEvent(self, event):
        import random
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(C_BG))
        if self.is_playing:
            self.bars = [random.randint(5, 40) for _ in self.bars]
        else:
            self.bars = [2] * 10
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C_ACCENT))
        for i, h in enumerate(self.bars):
            p.drawRect(i * 20 + 2, 50 - h, 16, h)


# ── Main Window ──────────────────────────────────────────────────────
class ArtThread(QThread):
    finished = Signal(bytes, str) # (data, type)

    def __init__(self, url, art_type):
        super().__init__()
        self.url = url
        self.art_type = art_type

    def run(self):
        import requests
        try:
            r = requests.get(self.url, timeout=5)
            if r.status_code == 200:
                self.finished.emit(r.content, self.art_type)
        except:
            pass

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # Services
        self.track_service    = TrackService()
        self.audio_engine     = AudioEngine()
        self.scraper_service  = WebScraperService()
        self.config_service   = ConfigService()
        self.queue_manager    = QueueManager(self.track_service, self.audio_engine)
        self.hotkey_service   = HotkeyService(self.audio_engine, self.queue_manager)
        self.download_service = DownloadService(self.config_service.get("download_dir"))

        # Job tracking  {job_id: {"row": list_row, "name": pack_name}}
        self._jobs = {}

        # Scraper threads
        self._scraper_threads = []

        # Signals
        self.audio_engine.playback_state_changed.connect(self._on_state_change)
        self.audio_engine.error_occurred.connect(self._on_audio_error)

        # Frameless Window Setup
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._drag_pos = QPoint()

        self._build_ui()
        self._refresh_library()
        self._load_consoles()

    # ─── UI Construction ────────────────────────────────────────────
    def _build_ui(self):
        self.setWindowTitle("CHIPTUNEPALACE // CONSOLE CATALOG")
        
        # Handle PyInstaller paths
        icon_path = "icon.png"
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, "icon.png")
            
        self.setWindowIcon(QIcon(icon_path))
        self.setFixedSize(QSize(1100, 900))
        self.setStyleSheet(GLOBAL_STYLE)

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)

        # Main Splitter: Left (Controls/Tabs) | Right (Now Playing Art)
        self.main_splitter = QSplitter(Qt.Horizontal)
        left_side = QWidget()
        left_l = QVBoxLayout(left_side)
        
        # --- LEFT SIDE CONTENT ---
        # Header row (Custom Title Bar)
        hdr = QHBoxLayout()
        title_label = QLabel("CHIPTUNEPALACE")
        title_label.setFont(QFont(FONT_PIXEL, 28, QFont.Bold))
        title_label.setStyleSheet(f"color: {C_ACCENT}; background: transparent;")
        hdr.addWidget(title_label)
        
        self.visualizer = PixelVisualizer()
        hdr.addWidget(self.visualizer)
        
        hdr.addStretch()
        
        # Window controls
        btn_min = QPushButton("_")
        btn_min.setFixedSize(30, 30)
        btn_min.clicked.connect(self.showMinimized)
        
        btn_close = QPushButton("X")
        btn_close.setFixedSize(30, 30)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet(f"QPushButton {{ border-color: {C_ACCENT}; color: {C_ACCENT}; }}")
        
        hdr.addWidget(btn_min)
        hdr.addWidget(btn_close)
        
        root_layout.addLayout(hdr)

        # Search bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("SEARCH WEB (e.g. Sonic, Zelda, Mega Man)...")
        self.search_input.returnPressed.connect(self._perform_search)
        btn_search = QPushButton("SEARCH")
        btn_search.clicked.connect(self._perform_search)
        search_row.addWidget(self.search_input)
        search_row.addWidget(btn_search)
        root_layout.addLayout(search_row)

        # Now-playing
        self.now_label = QLabel("SYSTEM READY // IDLE")
        self.now_label.setAlignment(Qt.AlignCenter)
        self.now_label.setFont(QFont(FONT_PIXEL, 13))
        root_layout.addWidget(self.now_label)

        # Tabs
        self.tabs = QTabWidget()

        # -- Tab 0: Catalog (Unified Tree) --------------------------------
        cat_w = QWidget()
        cat_l = QVBoxLayout(cat_w)
        
        self.catalog_tree = QTreeWidget()
        self.catalog_tree.setHeaderLabel("CONSOLE / GAME / TRACK")
        self.catalog_tree.itemExpanded.connect(self._on_tree_expanded)
        self.catalog_tree.itemDoubleClicked.connect(self._on_tree_dblclick)
        self.catalog_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.catalog_tree.customContextMenuRequested.connect(self._catalog_ctx)
        
        cat_l.addWidget(self.catalog_tree)
        self.tabs.addTab(cat_w, "CATALOG")

        # -- Tab 1: Search Results ----------------------------------------
        self.search_list = QListWidget()
        self.search_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.search_list.customContextMenuRequested.connect(self._search_ctx)
        self.search_list.itemDoubleClicked.connect(self._on_pack_dblclick)
        self.tabs.addTab(self.search_list, "SEARCH")

        # -- Tab 2: Library (individual files) ----------------------------
        self.library_list = QListWidget()
        self.library_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.library_list.customContextMenuRequested.connect(self._library_ctx)
        self.library_list.itemDoubleClicked.connect(self._play_library_item)
        self.tabs.addTab(self.library_list, "LIBRARY")

        # -- Tab 3: Settings ----------------------------------------------
        set_w = QWidget()
        set_l = QVBoxLayout(set_w)
        
        box = QGroupBox("DOWNLOAD PREFERENCES")
        form = QFormLayout(box)
        
        self.dir_input = QLineEdit(self.config_service.get("download_dir"))
        self.dir_input.setReadOnly(True)
        btn_browse = QPushButton("BROWSE")
        btn_browse.clicked.connect(self._browse_download_dir)
        
        row = QHBoxLayout()
        row.addWidget(self.dir_input)
        row.addWidget(btn_browse)
        
        form.addRow("Target Path:", row)
        set_l.addWidget(box)
        set_l.addStretch()
        
        self.tabs.addTab(set_w, "SETTINGS")

        left_l.addWidget(self.tabs, stretch=1)
        
        # ── Jobs panel ──────────────────────────────────────────────
        jobs_header = QLabel("ACTIVE JOBS")
        jobs_header.setFont(QFont(FONT_PIXEL, 11, QFont.Bold))
        jobs_header.setStyleSheet(f"color: {C_ACCENT};")
        left_l.addWidget(jobs_header)

        self.jobs_list = QListWidget()
        self.jobs_list.setFixedHeight(120)
        self.jobs_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.jobs_list.customContextMenuRequested.connect(self._jobs_ctx)
        left_l.addWidget(self.jobs_list)
        
        self.main_splitter.addWidget(left_side)

        # --- RIGHT SIDE (Now Playing Art) ---
        self.art_panel = QWidget()
        self.art_panel.setFixedWidth(300)
        art_l = QVBoxLayout(self.art_panel)
        
        art_header = QLabel("NOW PLAYING")
        art_header.setFont(QFont(FONT_PIXEL, 12, QFont.Bold))
        art_header.setStyleSheet(f"color: {C_ACCENT};")
        art_l.addWidget(art_header)
        
        self.cover_label = QLabel("NO COVER")
        self.cover_label.setFixedSize(280, 280)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet(f"border: 2px solid {C_ACCENT}; background: #000;")
        art_l.addWidget(self.cover_label)
        
        snap_header = QLabel("SCREENSHOT")
        snap_header.setFont(QFont(FONT_PIXEL, 10, QFont.Bold))
        snap_header.setStyleSheet(f"color: {C_CYAN};")
        art_l.addWidget(snap_header)
        
        self.snap_label = QLabel("NO SNAP")
        self.snap_label.setFixedSize(280, 210)
        self.snap_label.setAlignment(Qt.AlignCenter)
        self.snap_label.setStyleSheet(f"border: 2px solid {C_CYAN}; background: #000;")
        art_l.addWidget(self.snap_label)
        
        art_l.addStretch()
        
        self.main_splitter.addWidget(self.art_panel)
        root_layout.addWidget(self.main_splitter)

        # Transport controls
        ctl = QHBoxLayout()
        self.btn_prev = QPushButton("<<")
        self.btn_prev.clicked.connect(self.queue_manager.previous_track)
        self.btn_play = QPushButton("PLAY")
        self.btn_play.clicked.connect(self._toggle_play)
        self.btn_next = QPushButton(">>")
        self.btn_next.clicked.connect(self.queue_manager.advance_to_next_track)
        ctl.addWidget(self.btn_prev)
        ctl.addWidget(self.btn_play)
        ctl.addWidget(self.btn_next)
        root_layout.addLayout(ctl)

    # ─── Console catalog (Tree-based) ───────────────────────────────
    def _load_consoles(self):
        self.now_label.setText("INITIALIZING CONSOLE CATALOG...")
        thread = ScraperThread(self.scraper_service.get_consoles)
        thread.finished.connect(self._on_consoles_loaded)
        thread.error.connect(self._on_scraper_error)
        thread.start()
        self._scraper_threads.append(thread)

    def _on_consoles_loaded(self, consoles):
        self.catalog_tree.clear()
        for c in consoles:
            it = QTreeWidgetItem([c['name'].upper()])
            it.setData(0, Qt.UserRole, c['url'])
            it.setData(0, Qt.UserRole + 1, "console")
            # Add a dummy child to make it expandable
            dummy = QTreeWidgetItem(["Loading..."])
            it.addChild(dummy)
            self.catalog_tree.addTopLevelItem(it)
        self.now_label.setText(f"CATALOG: {len(consoles)} SYSTEMS READY.")

    def _on_tree_expanded(self, item):
        node_type = item.data(0, Qt.UserRole + 1)
        if node_type == "console":
            if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
                url = item.data(0, Qt.UserRole)
                name = item.text(0)
                self.now_label.setText(f"FETCHING GAMES FOR {name}...")
                thread = ScraperThread(self.scraper_service.get_packs_by_console, url)
                thread.finished.connect(lambda packs, i=item: self._on_tree_packs_loaded(packs, i))
                thread.error.connect(self._on_scraper_error)
                thread.start()
                self._scraper_threads.append(thread)
        elif node_type == "pack":
            if item.childCount() == 1 and item.child(0).text(0) == "Loading Tracks...":
                url = item.data(0, Qt.UserRole)
                title = item.text(0).replace(" [LOCAL]", "")
                self.now_label.setText(f"FETCHING TRACK LIST FOR {title}...")
                thread = ScraperThread(self.scraper_service.get_tracks_in_pack, url)
                thread.finished.connect(lambda tracks, i=item: self._on_tree_tracks_loaded(tracks, i))
                thread.error.connect(self._on_scraper_error)
                thread.start()
                self._scraper_threads.append(thread)

    def _on_tree_packs_loaded(self, packs, parent_item):
        parent_item.takeChild(0) # Remove "Loading..."
        for p in packs:
            it = QTreeWidgetItem([p['title']])
            it.setData(0, Qt.UserRole, p['url'])
            it.setData(0, Qt.UserRole + 1, "pack")
            
            # Check local
            is_local = False
            if self.track_service.db_manager.engine:
                conn = self.track_service.db_manager.engine.connect()
                from chiptunepalace.db.orm_stubs import tracks_table
                from sqlalchemy import select
                stmt = select(tracks_table.c.track_id).where(tracks_table.c.album == p['title']).limit(1)
                res = conn.execute(stmt).fetchone()
                if res: is_local = True
                conn.close()

            if is_local:
                it.setForeground(0, QColor(C_LIME)) # Using C_LIME from theme
                it.setText(0, f"{p['title']} [LOCAL]")
            
            # Add dummy child for track loading (if it's a pack and not a single module)
            if "vgmrips.net" in p['url']:
                dummy = QTreeWidgetItem(["Loading Tracks..."])
                it.addChild(dummy)
            
            parent_item.addChild(it)
        self.now_label.setText(f"LOADED {len(packs)} GAMES FOR {parent_item.text(0)}.")

    def _on_tree_tracks_loaded(self, tracks, parent_item):
        parent_item.takeChild(0) # Remove "Loading Tracks..."
        for t in tracks:
            it = QTreeWidgetItem([t['title']])
            it.setData(0, Qt.UserRole + 1, "track")
            parent_item.addChild(it)
        self.now_label.setText(f"PACK '{parent_item.text(0)}': {len(tracks)} TRACKS FOUND.")

    def _on_tree_dblclick(self, item, column):
        node_type = item.data(0, Qt.UserRole + 1)
        if node_type == "pack":
            self._on_pack_dblclick(item)
            
    def _catalog_ctx(self, pos):
        item = self.catalog_tree.itemAt(pos)
        if not item: return
        
        node_type = item.data(0, Qt.UserRole + 1)
        menu = QMenu()
        
        if node_type == "console":
            act_rename = QAction("Rename Console", self)
            act_rename.triggered.connect(lambda: self._rename_tree_item(item))
            menu.addAction(act_rename)

        elif node_type == "pack":
            dl_full = QAction("Save Game to Library (Extract)", self)
            dl_full.triggered.connect(lambda: self._on_pack_dblclick(item))
            dl_zip = QAction("Save Game to Library (ZIP Stream)", self)
            dl_zip.triggered.connect(lambda: self._dl_zip_only_from_item(item))
            menu.addAction(dl_full)
            menu.addAction(dl_zip)
            
        elif node_type == "track":
            act_save = QAction("Save Specific Track Metadata", self)
            act_save.triggered.connect(lambda: self.now_label.setText(f"SAVED: {item.text(0)}"))
            menu.addAction(act_save)
            
        menu.exec(self.catalog_tree.mapToGlobal(pos))

    def _rename_tree_item(self, item):
        from PySide6.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(self, "Rename", "Enter new name:", text=item.text(0))
        if ok and new_name:
            item.setText(0, new_name.upper())

    def _dl_zip_only_from_item(self, item):
        url = item.data(0, Qt.UserRole)
        name = item.text(0).replace(" [LOCAL]", "")
        job_id = self.download_service.download_pack(
            url, name,
            on_zip_ready=self._on_zip_ready,
            on_error=self._on_download_error,
            on_progress=self._on_download_progress,
            on_status=self._on_download_status,
            extract=False
        )
        row_text = f"[{job_id}] {name} (ZIP)  —  QUEUED"
        row_item = QListWidgetItem(row_text)
        self.jobs_list.addItem(row_item)
        self._jobs[job_id] = {"row": row_item, "name": name, "url": url}

    def _jobs_ctx(self, pos):
        item = self.jobs_list.itemAt(pos)
        if not item: return
        
        # Extract job ID from text "[JOB-001]..."
        text = item.text()
        if "[" in text and "]" in text:
            job_id = text[text.find("[")+1:text.find("]")]
            
            menu = QMenu()
            act_cancel = QAction("Cancel Download", self)
            act_cancel.triggered.connect(lambda: self.download_service.cancel_job(job_id))
            menu.addAction(act_cancel)
            menu.exec(self.jobs_list.mapToGlobal(pos))

    def _browse_download_dir(self):
        new_dir = QFileDialog.getExistingDirectory(self, "Select Download Folder", self.config_service.get("download_dir"))
        if new_dir:
            self.config_service.set("download_dir", new_dir)
            self.dir_input.setText(new_dir)
            self.download_service.download_dir = new_dir
            self.now_label.setText(f"SETTINGS: DOWNLOAD DIR UPDATED.")

    # ─── Search ─────────────────────────────────────────────────────
    def _perform_search(self):
        q = self.search_input.text().strip()
        if not q:
            return
        self.now_label.setText(f"SEARCHING: {q.upper()}...")
        thread = ScraperThread(self.scraper_service.search_online, q)
        thread.finished.connect(self._on_search_results)
        thread.error.connect(self._on_scraper_error)
        thread.start()
        self._scraper_threads.append(thread)

    def _on_search_results(self, results):
        self.search_list.clear()
        for r in results:
            it = QListWidgetItem(f"[{r['source']}] {r['title']}")
            it.setData(Qt.UserRole, r['url'])
            it.setData(Qt.UserRole + 1, r['source'])
            self.search_list.addItem(it)
        self.tabs.setCurrentIndex(1)
        self.now_label.setText(f"SEARCH: {len(results)} RESULTS.")

    def _search_ctx(self, pos):
        menu = QMenu()
        dl_full = QAction("Download & Extract", self)
        dl_full.triggered.connect(lambda: self._on_pack_dblclick(self.search_list.currentItem()))
        
        dl_zip = QAction("Stream from ZIP (Save Space)", self)
        dl_zip.triggered.connect(self._dl_zip_only)
        
        menu.addAction(dl_full)
        menu.addAction(dl_zip)
        menu.exec(self.search_list.mapToGlobal(pos))

    def _dl_zip_only(self):
        item = self.search_list.currentItem()
        if not item: return
        url = item.data(Qt.UserRole)
        name = item.text()
        
        job_id = self.download_service.download_pack(
            url, name,
            on_zip_ready=self._on_zip_ready,
            on_error=self._on_download_error,
            on_progress=self._on_download_progress,
            on_status=self._on_download_status,
            extract=False
        )
        row_text = f"[{job_id}] {name} (ZIP)  —  QUEUED"
        row_item = QListWidgetItem(row_text)
        self.jobs_list.addItem(row_item)
        self._jobs[job_id] = {"row": row_item, "name": name, "url": url}
        self.now_label.setText(f"ZIP DOWNLOAD STARTED: {name}")

    def _on_zip_ready(self, zip_path, job_id):
        info = self._jobs.get(job_id)
        if info:
            info["row"].setText(f"[{job_id}] {info['name']}  —  ZIP READY ✓")
        
        import zipfile
        added = 0
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for member in zf.namelist():
                if member.lower().endswith(('.vgm', '.vgz', '.nsf', '.spc', '.sid', '.mod', '.it', '.xm', '.s3m')):
                    # Metadata scraping from ZIP is harder without extraction, 
                    # but we can try to guess from filename or extract to memory
                    meta = {"title": os.path.basename(member), "artist": "Various"}
                    
                    # Calculate fingerprint from ZIP stream
                    fingerprint = self.track_service.db_manager.get_fingerprint(zip_path, member)
                    
                    self.track_service.add_track(
                        title=meta['title'],
                        artist=meta['artist'],
                        file_path=zip_path,
                        is_zipped=1,
                        member_name=member,
                        fingerprint=fingerprint,
                        source_url=info['url'] if info else None
                    )
                    added += 1
        
        self._refresh_library()
        self.tabs.setCurrentIndex(2)
        self.now_label.setText(f"REGISTERED {added} TRACKS FROM ZIP: {info['name'] if info else '??'}")

    def _on_scraper_error(self, msg):
        self.now_label.setText(f"SCRAPER ERROR // {msg[:40].upper()}")

    # ─── Download ───────────────────────────────────────────────────
    def _on_pack_dblclick(self, item):
        url  = item.data(Qt.UserRole)
        name = item.text()

        # Create a visible job row
        job_id = self.download_service.download_pack(
            url, name,
            on_finished=self._on_download_done,
            on_error=self._on_download_error,
            on_progress=self._on_download_progress,
            on_status=self._on_download_status,
        )
        row_text = f"[{job_id}] {name}  —  QUEUED"
        row_item = QListWidgetItem(row_text)
        self.jobs_list.addItem(row_item)
        self._jobs[job_id] = {"row": row_item, "name": name}
        self.now_label.setText(f"DOWNLOAD STARTED: {name}")

    def _on_download_progress(self, job_id, pct):
        info = self._jobs.get(job_id)
        if info:
            info["row"].setText(f"[{job_id}] {info['name']}  —  {pct}%")

    def _on_download_status(self, job_id, status):
        info = self._jobs.get(job_id)
        if info:
            info["row"].setText(f"[{job_id}] {info['name']}  —  {status}")

    def _on_download_done(self, folder_path, job_id):
        info = self._jobs.get(job_id)
        pack_name = info["name"] if info else "Unknown"
        if info:
            info["row"].setText(f"[{job_id}] {pack_name}  —  DONE ✓")

        # Scan extracted folder and add each individual file to the library
        added = 0
        for root, _dirs, files in os.walk(folder_path):
            for fname in sorted(files):
                if fname.lower().endswith(('.vgm', '.vgz', '.nsf', '.spc', '.sid', '.mod', '.it', '.xm', '.s3m')):
                    fpath = os.path.join(root, fname)
                    meta = self.scraper_service.scrape_metadata_for_file(fpath)
                    
                    # Calculate fingerprint for duplicate avoidance
                    fingerprint = self.track_service.db_manager.get_fingerprint(fpath)
                    
                    self.track_service.add_track(
                        title=meta['title'],
                        artist=meta['artist'],
                        file_path=fpath,
                        album=meta.get('album', pack_name),
                        genre=meta.get('genre', 'Chiptune'),
                        fingerprint=fingerprint,
                        source_url=None
                    )
                    added += 1

        self._refresh_library()
        self.tabs.setCurrentIndex(2)  # switch to LIBRARY
        self.now_label.setText(f"ADDED {added} TRACKS FROM: {pack_name}")

    def _on_download_error(self, msg, job_id):
        info = self._jobs.get(job_id)
        if info:
            info["row"].setText(f"[{job_id}] {info['name']}  —  FAILED ✗")
        self.now_label.setText(f"DOWNLOAD ERROR: {msg[:50]}")

    # ─── Library ────────────────────────────────────────────────────
    def _refresh_library(self):
        self.library_list.clear()
        tracks = self.track_service.get_all_tracks()
        for t in tracks:
            # Show individual file name alongside artist metadata
            fpath = t.get('file_path', '')
            fname = os.path.basename(fpath) if fpath else ''
            display = f"{fname}   [{t['artist']}]"
            it = QListWidgetItem(display)
            it.setData(Qt.UserRole, t['track_id'])
            self.library_list.addItem(it)
        track_ids = [t['track_id'] for t in tracks]
        self.queue_manager.load_playlist(track_ids)

    def _play_library_item(self, item):
        tid = item.data(Qt.UserRole)
        self.queue_manager.start_playback(tid)

    def _library_ctx(self, pos):
        menu = QMenu()
        act = QAction("Copy Path", self)
        act.triggered.connect(self._copy_path)
        menu.addAction(act)
        menu.exec(self.library_list.mapToGlobal(pos))

    def _copy_path(self):
        item = self.library_list.currentItem()
        if item:
            tid = item.data(Qt.UserRole)
            t = self.track_service.get_track_by_id(tid)
            QApplication.clipboard().setText(t['file_path'])

    # ─── Transport ────────────────────────────────────────────────
    def _toggle_play(self):
        if self.audio_engine.state == PlaybackState.PLAYING:
            self.audio_engine.pause()
        elif self.audio_engine.state == PlaybackState.PAUSED:
            self.audio_engine.play()
        else:
            self.queue_manager.start_playback()

    def _on_state_change(self, state):
        self.now_label.setText(f"STATE: {state.upper()}")
        if state == "Playing":
            self.visualizer.is_playing = True
            # Update artwork
            self._update_artwork()
        else:
            self.visualizer.is_playing = False
            self.visualizer.stop()

    def _update_artwork(self):
        track_id = self.queue_manager.get_current_track_id()
        if not track_id: return
        
        track = self.track_service.get_track_by_id(track_id)
        if not track: return
        
        # We need console name. Track info should ideally have it.
        # For now, we'll try to find it or use a default.
        console = track.get('console', 'SNES') # Defaulting for demo
        game = track.get('album', '')
        
        if not game: return
        
        art_urls = self.scraper_service.get_artwork(console, game)
        
        # Fetch in background
        self.box_thread = ArtThread(art_urls['boxart'], 'box')
        self.box_thread.finished.connect(self._on_art_finished)
        self.box_thread.start()
        
        self.snap_thread = ArtThread(art_urls['screenshot'], 'snap')
        self.snap_thread.finished.connect(self._on_art_finished)
        self.snap_thread.start()

    def _on_art_finished(self, data, art_type):
        pix = QPixmap()
        pix.loadFromData(data)
        if art_type == 'box':
            self.cover_label.setPixmap(pix.scaled(280, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.snap_label.setPixmap(pix.scaled(280, 210, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            tid = self.queue_manager.get_current_track_id()
            if tid:
                t = self.track_service.get_track_by_id(tid)
                fname = os.path.basename(t['file_path'])
                self.now_label.setText(f"NOW PLAYING // {fname.upper()}")
            self.btn_play.setText("PLAY")
            self.visualizer.stop()

    def _on_audio_error(self, msg):
        self.now_label.setText(f"ERROR // {msg[:40].upper()}")

    # ─── Frameless Dragging ─────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def closeEvent(self, event):
        self.hotkey_service.cleanup()
        for t in self._scraper_threads:
            if t.isRunning():
                t.terminate()
                t.wait()
        super().closeEvent(event)


# ── Entry ────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
