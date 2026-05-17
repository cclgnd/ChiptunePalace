import os
import zipfile
import re
from chiptunepalace.db.orm_stubs import DatabaseManager, Track


SUPPORTED_EXTS = {
    # SNES
    '.spc',
    # NES
    '.nsf', '.nsfe',
    # Game Boy / Game Boy Color
    '.gbs',
    # Game Boy Advance
    '.gsf', '.minigsf',
    # Nintendo DS
    '.2sf', '.mini2sf',
    # Nintendo 64
    '.usf', '.miniusf',
    # Sega Genesis / Mega Drive
    '.vgm', '.vgz', '.gym',
    # Sega Master System / Game Gear
    '.sgc',
    # Sega Saturn
    '.ssf', '.minissf',
    # Sega Dreamcast
    '.dsf', '.minidsf',
    # Sony PlayStation
    '.psf', '.minipsf',
    # Sony PlayStation 2
    '.psf2', '.minipsf2',
    # PC Engine / TurboGrafx-16
    '.hes',
    # Atari ST / Amstrad CPC / ZX Spectrum
    '.ym', '.vtx',
    # Commodore 64 / SID
    '.sid',
    # Amiga Tracker / ProTracker modules
    '.mod', '.xm', '.it', '.s3m',
    # Other classic module formats
    '.stm', '.mtm', '.okt', '.med',
    # Standard modern formats (natively decoded by VLC)
    '.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a', '.wma'
}


class TrackService:
    """Handles all database interactions and indexing related to tracks."""

    def __init__(self):
        self.db_manager = DatabaseManager()

    def get_all_tracks(self):
        """Returns a list of dicts, one per track."""
        return self.db_manager.get_all_tracks()

    def get_track_by_id(self, track_id: int):
        """Returns a single track dict or None."""
        return self.db_manager.get_track_by_id(track_id)

    def add_track(self, title: str, artist: str, file_path: str, **kwargs):
        """Adds a new track; returns the track_id."""
        return self.db_manager.add_track(title, artist, file_path, **kwargs)

    def index_zip_pack(self, zip_path: str, console_name: str, game_name: str, source_url: str = None) -> list:
        """
        Scans a downloaded ZIP file for track extensions, calculates MD5 content fingerprints,
        and adds them to the database for instant ZIP streaming.
        """
        indexed_ids = []
        fingerprint = self.db_manager.get_fingerprint(zip_path)
        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.namelist():
                    # Normalize extension checking
                    ext = os.path.splitext(member)[1].lower()
                    if ext in SUPPORTED_EXTS:
                        base_name = os.path.basename(member)
                        if not base_name:
                            continue
                        
                        # Extract title and clean it up
                        title = os.path.splitext(base_name)[0]
                        # Strip common track number prefixes like "01 - ", "04_", etc.
                        title = re.sub(r'^\d+[\s\-_]*', '', title).replace('_', ' ').strip()
                        
                        # Add track to DB (duplicate avoidance handled by add_track internally)
                        track_id = self.db_manager.add_track(
                            title=title,
                            artist="Various",
                            console=console_name,
                            game=game_name,
                            file_path=zip_path,
                            member_name=member,
                            fingerprint=fingerprint,
                            source_url=source_url,
                            format=ext[1:].upper()
                        )
                        indexed_ids.append(track_id)
            print(f"TrackService: Indexed {len(indexed_ids)} tracks from ZIP {zip_path}")
        except Exception as e:
            print(f"TrackService: Failed to index ZIP {zip_path}: {e}")
        return indexed_ids

    def get_tracks_by_console_and_game(self, console_name: str, game_name: str) -> list:
        """Returns all tracks belonging to a specific console and game."""
        session = self.db_manager.Session()
        try:
            tracks = session.query(Track).filter(
                Track.console == console_name,
                Track.game == game_name
            ).order_by(Track.title).all()
            return [self.db_manager._to_dict(t) for t in tracks]
        finally:
            session.close()

    def get_library_hierarchy(self) -> dict:
        """
        Returns a nested dictionary representing the local library catalog:
        { ConsoleName: { GameName: [TrackDicts] } }
        """
        all_tracks = self.get_all_tracks()
        catalog = {}
        for t in all_tracks:
            console = t.get('console', 'Unknown Console')
            game = t.get('game', 'Unknown Game')
            if console not in catalog:
                catalog[console] = {}
            if game not in catalog[console]:
                catalog[console][game] = []
            catalog[console][game].append(t)
        return catalog
