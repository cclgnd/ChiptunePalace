import os
import sys
import zipfile
import gzip
import io
from PySide6.QtCore import QObject, Signal

from audio.backends.gme_backend import GmeBackend
from audio.output.sounddevice_output import SoundDeviceOutput
from audio.core.format_detector import is_emulation_supported

class PlaybackState:
    PLAYING = "Playing"
    PAUSED = "Paused"
    STOPPED = "Stopped"
    ERROR = "Error"

class AudioEngine(QObject):
    # Public signals replicating the original AudioEngine interface exactly
    playback_state_changed = Signal(str)
    track_finished = Signal()
    error_occurred = Signal(str)
    warning_occurred = Signal(str)
    volume_changed = Signal(int)
    position_changed = Signal(float)  # seconds
    duration_changed = Signal(float)  # seconds

    def __init__(self, sample_rate: int = 44100):
        super().__init__()
        
        # Core components
        self._backend = GmeBackend(sample_rate=sample_rate)
        self._output = SoundDeviceOutput(sample_rate=sample_rate)
        
        # Connect output signals
        self._output.playback_state_changed.connect(self._on_state_changed)
        self._output.position_changed.connect(self._on_position_changed)
        self._output.duration_changed.connect(self._on_duration_changed)
        self._output.track_finished.connect(self.track_finished)
        self._output.error_occurred.connect(self.error_occurred)
        self._output.warning_occurred.connect(self.warning_occurred)
        
        # Initial settings
        self._volume = 80
        self._output.set_volume(0.8)
        self._output.set_backend(self._backend)
        
        print("AudioEngine (Emulation): Initialized successfully.")

    def _on_state_changed(self, state: str):
        self.playback_state_changed.emit(state)

    def _on_position_changed(self, pos_ms: int):
        self.position_changed.emit(pos_ms / 1000.0)

    def _on_duration_changed(self, dur_ms: int):
        self.duration_changed.emit(dur_ms / 1000.0)

    @property
    def state(self) -> str:
        return self._output.get_state()

    def load_track(self, track_path: str, member_name: str = None) -> bool:
        """Loads a track into the emulator backend directly from memory."""
        self.stop()
        
        track_path = os.path.abspath(track_path)
        if not os.path.exists(track_path):
            self.error_occurred.emit(f"File not found: {track_path}")
            return False

        success = False
        # Check if it's a zip file
        if zipfile.is_zipfile(track_path):
            try:
                with zipfile.ZipFile(track_path, 'r') as zf:
                    target_member = member_name
                    if not target_member:
                        # Find the first member that GME supports
                        for name in zf.namelist():
                            if is_emulation_supported(name):
                                target_member = name
                                break
                    if not target_member:
                        self.error_occurred.emit(f"No supported emulation file found in ZIP: {track_path}")
                        return False
                        
                    with zf.open(target_member) as mf:
                        data = mf.read()
                        
                    # Decompress VGZ if inside ZIP
                    if target_member.lower().endswith(".vgz"):
                        try:
                            with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                                data = gz.read()
                        except Exception as e:
                            self.error_occurred.emit(f"VGZ decompression inside ZIP failed: {e}")
                            return False
                    
                    success = self._backend.load(data, filename=target_member)
            except Exception as e:
                self.error_occurred.emit(f"Failed to read ZIP member: {e}")
                return False
        else:
            # Check standalone VGZ file
            if track_path.lower().endswith(".vgz"):
                try:
                    with gzip.open(track_path, 'rb') as gz:
                        data = gz.read()
                    success = self._backend.load(data, filename=track_path)
                except Exception as e:
                    self.error_occurred.emit(f"Failed to decompress standalone VGZ: {e}")
                    return False
            else:
                # Standalone uncompressed file
                success = self._backend.load(track_path, filename=track_path)

        if success:
            # Tell output we have a new backend loaded to trigger duration/position updates
            self._output.set_backend(self._backend)
            return True
        else:
            self.error_occurred.emit("Failed to load track into emulator backend")
            return False

    def play(self):
        """Starts playback using sounddevice output."""
        self._output.play()

    def pause(self):
        """Pauses playback."""
        self._output.pause()

    def stop(self):
        """Stops playback."""
        self._output.stop()
        self._backend.close()

    def set_volume(self, volume: int):
        """Sets volume from 0 to 100."""
        self._volume = max(0, min(100, int(volume)))
        self._output.set_volume(self._volume / 100.0)
        self.volume_changed.emit(self._volume)

    def get_time(self) -> float:
        """Gets current position in seconds."""
        return self._backend.get_position_ms() / 1000.0

    def set_time(self, seconds: float):
        """Seeks to the given position in seconds."""
        self._backend.seek(int(seconds * 1000.0))
        self.position_changed.emit(seconds)

    def close(self):
        self.stop()
        self._output.close()
        self._backend.close()

    def __del__(self):
        try:
            self.close()
        except:
            pass
