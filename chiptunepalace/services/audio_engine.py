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
    warning_occurred = Signal(str)
    volume_changed = Signal(int)
    position_changed = Signal(float)  # seconds
    duration_changed = Signal(float)  # seconds

    _GZIP_EXTS = {".vgz"}

    # Map of all emulated platforms to their respective legacy decoders (if any)
    _TRANSCODE_EXTS = {
        '.spc': 'vgmstream-cli.exe',
        '.vgm': 'VGMPlay.exe',
        '.vgz': 'VGMPlay.exe',
        '.ssf': 'vgmstream-cli.exe',
        '.minissf': 'vgmstream-cli.exe',
        '.dsf': 'vgmstream-cli.exe',
        '.minidsf': 'vgmstream-cli.exe',
        '.psf': 'vgmstream-cli.exe',
        '.minipsf': 'vgmstream-cli.exe',
        '.gsf': 'vgmstream-cli.exe',
        '.minigsf': 'vgmstream-cli.exe',
        '.nsf': 'nsf2wav.exe',
        '.nsfe': 'nsf2wav.exe',
        '.gbs': 'gbs2wav.exe',
        '.hes': 'hes2wav.exe',
        '.sid': 'sid2wav.exe',
        '.sgc': 'sgc2wav.exe',
        '.gym': 'gym2wav.exe',
        '.psf2': 'psf2play-cli.exe',
        '.minipsf2': 'psf2play-cli.exe',
        '.usf': 'usf2wav.exe',
        '.miniusf': 'usf2wav.exe',
        '.2sf': '2sf2wav.exe',
        '.mini2sf': '2sf2wav.exe',
        '.ym': 'ymplay-cli.exe',
        '.vtx': 'ymplay-cli.exe',
    }

    # Formats natively and cleanly supported by the vendor build of vgmstream-cli.exe
    _VGMSTREAM_SUPPORTED_EXTS = {
        '.spc', '.ssf', '.minissf', '.dsf', '.minidsf', '.psf', '.minipsf', '.gsf', '.minigsf'
    }

    def __init__(self):
        super().__init__()
        from chiptunepalace.services.debug_service import DebugService
        self.debug_service = DebugService()
        
        try:
            self.vlc_instance = vlc.Instance("--no-video")
            self.player = self.vlc_instance.media_player_new()
            self._available = True
            self.debug_service.log_info("AudioEngine: VLC Instance initialized successfully.")
        except Exception as e:
            self.vlc_instance = None
            self.player = None
            self._available = False
            self.debug_service.log_error(f"AudioEngine: VLC Initialization failed: {e}")
            print(f"FATAL: VLC Initialization failed: {e}")

        self._state = PlaybackState.STOPPED
        self._current_track_path = None
        self._temp_path = None
        self._volume = 80
        
        # Setup event manager for end of track
        if self.player:
            self.event_manager = self.player.event_manager()
            self.event_manager.event_attach(vlc.EventType.MediaPlayerEndReached, self._on_end_reached)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerPositionChanged, self._on_position_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerLengthChanged, self._on_length_changed)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerPlaying, self._on_playing)
            self.event_manager.event_attach(vlc.EventType.MediaPlayerEncounteredError, self._on_error)

    def _on_position_changed(self, event):
        if self.player:
            time_ms = self.player.get_time()
            self.position_changed.emit(time_ms / 1000.0)

    def _on_length_changed(self, event):
        if self.player:
            length_ms = self.player.get_length()
            self.duration_changed.emit(length_ms / 1000.0)

    def _on_end_reached(self, event):
        self.track_finished.emit()

    def _on_playing(self, event):
        if self.player:
            # Set the volume once the audio output device has been successfully initialized asynchronously
            self.player.audio_set_volume(self._volume)

    def _on_error(self, event):
        self.error_occurred.emit("VLC encountered a playback error. The file format may be unsupported or the file is corrupted.")

    def _prepare_path(self, path, member_name=None):
        """Decompress .vgz, extract from ZIP, and/or transcode emulated chiptunes to a temp WAV file."""
        path = os.path.abspath(path)
        self._cleanup_temp()
        
        # 1. Handle ZIP member
        current_file_path = path
        if member_name:
            import zipfile
            try:
                ext = os.path.splitext(member_name)[1].lower()
                with zipfile.ZipFile(path, 'r') as zf:
                    data = zf.read(member_name)
                
                # If the extracted member itself is a .vgz file, decompress it!
                if ext == ".vgz":
                    import io
                    with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
                        data = gz.read()
                    ext = ".vgm"
                    
                tmp = tempfile.NamedTemporaryFile(
                    suffix=ext, delete=False, prefix="cp_zip_"
                )
                tmp.write(data)
                tmp.close()
                self._temp_path = tmp.name
                current_file_path = tmp.name
            except Exception as e:
                self.error_occurred.emit(f"ZIP extraction error: {e}")
                return path

        # 2. Handle VGZ (standalone or extracted from ZIP)
        ext = os.path.splitext(current_file_path)[1].lower()
        if ext in self._GZIP_EXTS:
            try:
                with gzip.open(current_file_path, "rb") as gz:
                    data = gz.read()
                tmp = tempfile.NamedTemporaryFile(
                    suffix=".vgm", delete=False, prefix="cp_"
                )
                tmp.write(data)
                tmp.close()
                self._temp_path = tmp.name
                current_file_path = tmp.name
                ext = ".vgm"
            except Exception as e:
                self.error_occurred.emit(f"Decompression error: {e}")
                return current_file_path

        # 3. Handle emulated formats transcoding to WAV
        if ext in self._TRANSCODE_EXTS:
            try:
                transcoded_path = self._transcode_to_wav(current_file_path, ext)
                if transcoded_path:
                    # Cleanup intermediate ZIP/VGZ temp paths
                    if self._temp_path and self._temp_path != transcoded_path:
                        try:
                            os.unlink(self._temp_path)
                        except:
                            pass
                    self._temp_path = transcoded_path
                    return transcoded_path
            except Exception as e:
                self.error_occurred.emit(f"Transcoding error: {e}")
                
        return current_file_path

    def _transcode_to_wav(self, file_path, ext):
        """Transcode emulated chiptunes to a temporary WAV file using vendor CLI decoders or VGMStream."""
        import subprocess
        import time
        
        vendor_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "vendor", "bin"
        )
        
        vgmstream_exe = os.path.join(vendor_dir, "vgmstream-cli.exe")
        
        # 1. Custom robust handler for VGMPlay.exe (handles .vgm and .vgz)
        if ext in {".vgm", ".vgz"}:
            vgmplay_exe = os.path.join(vendor_dir, "VGMPlay.exe")
            vgmplay_ini = os.path.join(vendor_dir, "VGMPlay.ini")
            
            if os.path.exists(vgmplay_exe) and os.path.exists(vgmplay_ini):
                self.debug_service.log_info(f"AudioEngine: Transcoding {ext} using VGMPlay")
                
                # Read original ini
                ini_content = None
                try:
                    with open(vgmplay_ini, "r") as f:
                        ini_content = f.read()
                except Exception as e:
                    self.debug_service.log_error(f"AudioEngine: Failed to read VGMPlay.ini: {e}")
                
                if ini_content:
                    # Modify ini for silent logging
                    modified_ini = []
                    for line in ini_content.splitlines():
                        if line.strip().startswith("LogSound ="):
                            modified_ini.append("LogSound = 1")
                        elif line.strip().startswith("MaxLoops ="):
                            modified_ini.append("MaxLoops = 1")
                        else:
                            modified_ini.append(line)
                    
                    try:
                        with open(vgmplay_ini, "w") as f:
                            f.write("\n".join(modified_ini))
                    except Exception as e:
                        self.debug_service.log_error(f"AudioEngine: Failed to write VGMPlay.ini: {e}")
                
                # The output WAV path will be in the same folder as file_path
                wav_path = os.path.splitext(file_path)[0] + ".wav"
                if os.path.exists(wav_path):
                    try:
                        os.unlink(wav_path)
                    except:
                        pass
                
                p = None
                success = False
                try:
                    p = subprocess.Popen(
                        [vgmplay_exe, file_path],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        cwd=vendor_dir,
                        text=True
                    )
                    
                    # Monitor WAV growth
                    last_size = -1
                    no_change_count = 0
                    
                    # Max wait 10 seconds (100 * 0.1s)
                    for _ in range(100):
                        time.sleep(0.1)
                        if os.path.exists(wav_path):
                            current_size = os.path.getsize(wav_path)
                            if current_size > 0 and current_size == last_size:
                                no_change_count += 1
                                if no_change_count >= 2:  # stabilized
                                    success = True
                                    break
                            else:
                                no_change_count = 0
                            last_size = current_size
                    
                    # Terminate process cleanly
                    try:
                        p.stdin.write("q\n")
                        p.stdin.flush()
                    except:
                        pass
                    finally:
                        try:
                            p.stdin.close()
                        except:
                            pass
                    
                    try:
                        p.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        p.kill()
                except Exception as e:
                    self.debug_service.log_error(f"AudioEngine: VGMPlay process error: {e}")
                    if p:
                        try:
                            p.kill()
                        except:
                            pass
                finally:
                    # Restore original ini
                    if ini_content:
                        try:
                            with open(vgmplay_ini, "w") as f:
                                f.write(ini_content)
                        except Exception as e:
                            self.debug_service.log_error(f"AudioEngine: Failed to restore VGMPlay.ini: {e}")
                
                if success and os.path.exists(wav_path):
                    self.debug_service.log_info(f"AudioEngine: VGMPlay transcoding successful: {wav_path}")
                    return wav_path
                else:
                    self.debug_service.log_error("AudioEngine: VGMPlay transcoding failed or timed out. Falling back to mock synth.")
            
            # Fallback to mock wav if VGMPlay.exe not found or fails
            tmp_wav = tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, prefix="cp_transcode_"
            )
            tmp_wav.close()
            self._write_mock_wav(tmp_wav.name)
            self.warning_occurred.emit(f"Transcoding failed for {ext}. Playing mock synth fallback.")
            return tmp_wav.name
            
        # 2. General handler for other formats
        # Create a temporary WAV file path
        tmp_wav = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False, prefix="cp_transcode_"
        )
        tmp_wav.close()
        
        # Determine if we can use vgmstream for this format
        use_vgmstream = (ext in self._VGMSTREAM_SUPPORTED_EXTS) and os.path.exists(vgmstream_exe)
        
        if use_vgmstream:
            cmd = [vgmstream_exe, "-o", tmp_wav.name, file_path]
            self.debug_service.log_info(f"AudioEngine: Transcoding {ext} using VGMStream: {cmd}")
            try:
                subprocess.run(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                    timeout=5.0, check=True
                )
                self.debug_service.log_info(f"AudioEngine: VGMStream transcoding successful: {tmp_wav.name}")
                return tmp_wav.name
            except Exception as e:
                self.debug_service.log_error(f"AudioEngine: VGMStream transcoding failed for {ext}: {e}. Falling back to mock synth.")
                print(f"AudioEngine: VGMStream transcoding failed for {ext}: {e}. Falling back to mock synth.")
                self._write_mock_wav(tmp_wav.name)
                self.warning_occurred.emit(f"Transcoding failed for {ext}: {e}. Playing mock synth fallback.")
                return tmp_wav.name
        else:
            # Check if there is a specific custom decoder executable mapped for this format
            bin_name = self._TRANSCODE_EXTS.get(ext)
            exe_path = os.path.join(vendor_dir, bin_name) if bin_name else None
            
            if exe_path and os.path.exists(exe_path):
                if "upse123" in bin_name:
                    cmd = [exe_path, "-w", tmp_wav.name, file_path]
                else:
                    cmd = [exe_path, file_path, tmp_wav.name]
                self.debug_service.log_info(f"AudioEngine: Transcoding {ext} using legacy decoder: {cmd}")
                try:
                    subprocess.run(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                        timeout=5.0, check=True
                    )
                    self.debug_service.log_info(f"AudioEngine: Legacy transcoding successful: {tmp_wav.name}")
                    return tmp_wav.name
                except Exception as e:
                    self.debug_service.log_error(f"AudioEngine: Legacy transcoding failed for {ext}: {e}. Falling back to mock synth.")
                    print(f"AudioEngine: Legacy transcoding failed for {ext}: {e}. Falling back to mock synth.")
                    self._write_mock_wav(tmp_wav.name)
                    return tmp_wav.name
            else:
                # No decoder or missing decoder: write high-fidelity retro synth tone
                self.debug_service.log_warning(f"AudioEngine: Required decoder '{bin_name}' for '{ext}' missing. Generating mock synth tone.")
                self._write_mock_wav(tmp_wav.name)
                # Show standard message
                self.warning_occurred.emit(
                    f"Chiptune Sound Engine Warning: Required decoder for '{ext}' is missing from '{vendor_dir}'. "
                    "Playing high-fidelity mock synth tone."
                )
                return tmp_wav.name

    def _write_mock_wav(self, file_path):
        """Generates a standard 1-second high-quality sine wave WAV file dynamically using standard library."""
        import struct
        import math
        
        sample_rate = 22050
        duration = 1.0
        num_samples = int(sample_rate * duration)
        frequency = 440.0
        
        pcm_data = bytearray()
        for i in range(num_samples):
            value = int(16384.0 * math.sin(2.0 * math.pi * frequency * i / sample_rate))
            pcm_data.extend(struct.pack("<h", value))
            
        num_channels = 1
        bytes_per_sample = 2
        byte_rate = sample_rate * num_channels * bytes_per_sample
        block_align = num_channels * bytes_per_sample
        data_chunk_size = len(pcm_data)
        riff_chunk_size = 36 + data_chunk_size
        
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", riff_chunk_size, b"WAVE",
            b"fmt ", 16, 1, num_channels, sample_rate, byte_rate, block_align, 16,
            b"data", data_chunk_size
        )
        
        try:
            with open(file_path, "wb") as f:
                f.write(header)
                f.write(pcm_data)
        except Exception as e:
            print(f"Error writing mock WAV: {e}")

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
            self.debug_service.log_error("AudioEngine: Cannot load track, VLC is not available")
            self.error_occurred.emit("VLC not available")
            return False

        try:
            self.debug_service.log_info(f"AudioEngine: Loading track path={track_path} member={member_name}")
            actual_path = self._prepare_path(track_path, member_name)
            media = self.vlc_instance.media_new_path(actual_path)
            self.player.set_media(media)
            self._current_track_path = track_path
            print(f"AudioEngine: Loaded track {track_path} (member: {member_name})")
            return True
        except Exception as e:
            self.debug_service.log_error(f"AudioEngine: Failed to load track: {e}")
            self.error_occurred.emit(f"Failed to load track: {e}")
            return False

    def play(self):
        """Starts playback."""
        if self.player:
            self.debug_service.log_info("AudioEngine: Playback started")
            self.player.play()
            self.player.audio_set_volume(self._volume)
            self._state = PlaybackState.PLAYING
            self.playback_state_changed.emit(PlaybackState.PLAYING)
        
    def pause(self):
        """Pauses the current playback."""
        if self.player and self._state == PlaybackState.PLAYING:
            self.debug_service.log_info("AudioEngine: Playback paused")
            self.player.pause()
            self._state = PlaybackState.PAUSED
            self.playback_state_changed.emit(PlaybackState.PAUSED)

    def stop(self):
        """Stops playback and resets state."""
        if self.player:
            self.debug_service.log_info("AudioEngine: Playback stopped")
            self.player.stop()
            self._state = PlaybackState.STOPPED
            self.playback_state_changed.emit(PlaybackState.STOPPED)
            self._cleanup_temp()

    def set_volume(self, volume):
        self._volume = max(0, min(100, int(volume)))
        self.debug_service.log_info(f"AudioEngine: Volume set to {self._volume}%")
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
        self.debug_service.log_info(f"AudioEngine: Seek requested to {seconds}s")
        if self.player:
            self.player.set_time(int(seconds * 1000))

    def __del__(self):
        self._cleanup_temp()
