import gzip
import os
import tempfile
import vlc
from PySide6.QtCore import QObject, Signal, QUrl

class PlaybackState:
    """Defines the possible states of the player."""
    PLAYING = "Playing"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    ERROR = "Error"

class AudioEngine(QObject):
    """
    Manages all audio streaming and playback functionality using python-vlc.
    Includes a bridge for .vgz (compressed .vgm) files.
    """
    # Signals to communicate state changes back to the GUI
    playback_state_changed = Signal(str)
    track_finished = Signal()
    error_occurred = Signal(str)
    volume_changed = Signal(int)

    _GZIP_EXTS = {".vgz"}

    def __init__(self):
        super().__init__()
        try:
            self.vlc_instance = vlc.Instance("--no-video")
            self.player = self.vlc_instance.media_player_new()
            self._available = True
        except Exception as e:
            self.vlc_instance = None
            self.player = None
            self._available = False
            print(f"FATAL: VLC Initialization failed: {e}")

        self._state = PlaybackState.STOPPED
        self._current_track_path = None
        self._temp_path = None
        self._volume = 80
        
        # Setup event manager for end of track
        if self.player:
            self.event_manager = self.player.event_manager()
            self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)

    def _on_end_reached(self, event):
        self.track_finished.emit()

    def _prepare_path(self, path, member_name=None):
        """Decompress .vgz or extract from ZIP to a temp file; return usable path."""
        self._cleanup_temp()
        
        # 1. Handle ZIP member
        if member_name:
            import zipfile
            try:
                ext = os.path.splitext(member_name)[1].lower()
                with zipfile.ZipFile(path, 'r') as zf:
                    data = zf.read(member_name)
                tmp = tempfile.NamedTemporaryFile(
                    suffix=ext, delete=False, prefix="cp_zip_"
                )
                tmp.write(data)
                tmp.close()
                self._temp_path = tmp.name
                return tmp.name
            except Exception as e:
                self.error_occurred.emit(f"ZIP extraction error: {e}")
                return path

        # 2. Handle VGZ
        ext = os.path.splitext(path)[1].lower()
        if ext in self._GZIP_EXTS:
            try:
                with gzip.open(path, "rb") as gz:
                    data = gz.read()
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".vgm", delete=False, prefix="cp_"
                )
                tmp.write(data)
                tmp.close()
                self._temp_path = tmp.name
                return tmp.name
            except Exception as e:
                self.error_occurred.emit(f"Decompression error: {e}")
        return path

    def _cleanup_temp(self):
        if self._temp_path:
            try:
                os.unlink(self._temp_path)
            except OSError:
                pass
            self._temp_path = None

    @property
    def state(self):
        return self._state

    def load_track(self, track_path: str, member_name: str = None):
        """Loads a new track source."""
        if not self._available:
            self.error_occurred.emit("VLC not available")
            return False

        try:
            actual_path = self._prepare_path(track_path, member_name)
            media = self.vlc_instance.media_new_path(actual_path)
            self.player.set_media(media)
            self._current_track_path = track_path
            print(f"AudioEngine: Loaded track {track_path} (member: {member_name})")
            return True
        except Exception as e:
            self.error_occurred.emit(f"Failed to load track: {e}")
            return False

    def play(self):
        """Starts playback."""
        if self.player:
            self.player.play()
            self.player.audio_set_volume(self._volume)
            self._state = PlaybackState.PLAYING
            self.playback_state_changed.emit(PlaybackState.PLAYING)
        
    def pause(self):
        """Pauses the current playback."""
        if self.player and self._state == PlaybackState.PLAYING:
            self.player.pause()
            self._state = PlaybackState.PAUSED
            self.playback_state_changed.emit(PlaybackState.PAUSED)

    def stop(self):
        """Stops playback and resets state."""
        if self.player:
            self.player.stop()
            self._state = PlaybackState.STOPPED
            self.playback_state_changed.emit(PlaybackState.STOPPED)
            self._cleanup_temp()

    def set_volume(self, volume):
        self._volume = max(0, min(100, int(volume)))
        if self.player:
            self.player.audio_set_volume(self._volume)
        self.volume_changed.emit(self._volume)

    def get_time(self):
        """Returns current time in seconds."""
        if self.player:
            return self.player.get_time() / 1000.0
        return 0.0

    def set_time(self, seconds):
        """Seeks to the given time in seconds."""
        if self.player:
            self.player.set_time(int(seconds * 1000))

    def __del__(self):
        self._cleanup_temp()
