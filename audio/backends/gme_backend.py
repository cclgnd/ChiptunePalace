import os
import sys
import ctypes
import numpy as np
from audio.backends.base import EmulatorBackend

# Define GmeInfoT exactly as reverse engineered
class GmeInfoT(ctypes.Structure):
    _fields_ = [
        ("ints", ctypes.c_int * 16),  # 64 bytes of integers
        ("system", ctypes.c_char_p),
        ("game", ctypes.c_char_p),
        ("song", ctypes.c_char_p),
        ("author", ctypes.c_char_p),
        ("copyright", ctypes.c_char_p),
        ("comment", ctypes.c_char_p),
        ("dumper", ctypes.c_char_p),
    ]

class GmeBackend(EmulatorBackend):
    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate
        self._emu = None
        self._loaded = False
        self._volume = 0.8
        self._gme = None
        self._duration_ms = -1
        self._current_track = 0
        
        # Load gme.dll
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            possible_paths = [
                os.path.abspath(os.path.join(current_dir, "..", "..", "chiptunepalace", "vendor", "bin", "gme.dll")),
                os.path.abspath(os.path.join(current_dir, "..", "..", "vendor", "bin", "gme.dll")),
                "gme.dll"
            ]
            
            for path in possible_paths:
                if isinstance(path, str) and not os.path.exists(path) and path != "gme.dll":
                    continue
                try:
                    self._gme = ctypes.CDLL(path)
                    break
                except Exception:
                    continue
            
            if not self._gme:
                raise RuntimeError("Could not find or load gme.dll")
                
            # Declare function signatures
            self._setup_signatures()
        except Exception as e:
            print(f"GmeBackend: Initialization failed: {e}", file=sys.stderr)
            self._gme = None

    def _setup_signatures(self):
        gme = self._gme
        
        gme.gme_open_data.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.POINTER(ctypes.c_void_p), ctypes.c_int]
        gme.gme_open_data.restype = ctypes.c_char_p
        
        gme.gme_delete.argtypes = [ctypes.c_void_p]
        gme.gme_delete.restype = None
        
        gme.gme_track_count.argtypes = [ctypes.c_void_p]
        gme.gme_track_count.restype = ctypes.c_int
        
        gme.gme_start_track.argtypes = [ctypes.c_void_p, ctypes.c_int]
        gme.gme_start_track.restype = ctypes.c_char_p
        
        gme.gme_play.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_short)]
        gme.gme_play.restype = ctypes.c_char_p
        
        gme.gme_track_info.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.POINTER(GmeInfoT)), ctypes.c_int]
        gme.gme_track_info.restype = ctypes.c_char_p
        
        gme.gme_free_info.argtypes = [ctypes.POINTER(GmeInfoT)]
        gme.gme_free_info.restype = None
        
        gme.gme_tell.argtypes = [ctypes.c_void_p]
        gme.gme_tell.restype = ctypes.c_int
        
        gme.gme_seek.argtypes = [ctypes.c_void_p, ctypes.c_int]
        gme.gme_seek.restype = ctypes.c_char_p
        
        gme.gme_mute_voice.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
        gme.gme_mute_voice.restype = None
        
        gme.gme_voice_count.argtypes = [ctypes.c_void_p]
        gme.gme_voice_count.restype = ctypes.c_int

    def load(self, data: bytes | str, filename: str = "") -> bool:
        if not self._gme:
            return False
            
        self.close()
        
        # Resolve data (read from path if string)
        if isinstance(data, str):
            try:
                with open(data, "rb") as f:
                    file_data = f.read()
            except Exception as e:
                print(f"GmeBackend Error: Failed to read file {data}: {e}", file=sys.stderr)
                return False
        else:
            file_data = data
            
        # Open data in emulator
        emu_ptr = ctypes.c_void_p()
        err = self._gme.gme_open_data(file_data, len(file_data), ctypes.byref(emu_ptr), self.sample_rate)
        if err:
            err_msg = err.decode('utf-8', 'ignore') if isinstance(err, bytes) else str(err)
            print(f"GmeBackend Error: gme_open_data failed: {err_msg}", file=sys.stderr)
            return False
            
        self._emu = emu_ptr
        self._loaded = True
        self._current_track = 0
        
        # Start the track
        err = self._gme.gme_start_track(self._emu, self._current_track)
        if err:
            err_msg = err.decode('utf-8', 'ignore') if isinstance(err, bytes) else str(err)
            print(f"GmeBackend Error: gme_start_track failed: {err_msg}", file=sys.stderr)
            self.close()
            return False
            
        # Get track info / duration
        self._fetch_metadata()
        
        return True

    def _fetch_metadata(self):
        if not self._emu:
            return
            
        info_ptr = ctypes.POINTER(GmeInfoT)()
        err = self._gme.gme_track_info(self._emu, ctypes.byref(info_ptr), self._current_track)
        if not err and info_ptr:
            info = info_ptr.contents
            self._duration_ms = info.ints[0]
            if self._duration_ms <= 0:
                self._duration_ms = info.ints[3] if info.ints[3] > 0 else 150000
            
            system = info.system.decode('utf-8', 'ignore') if info.system else "Unknown"
            game = info.game.decode('utf-8', 'ignore') if info.game else "Unknown"
            song = info.song.decode('utf-8', 'ignore') if info.song else "Unknown"
            author = info.author.decode('utf-8', 'ignore') if info.author else "Unknown"
            print(f"GmeBackend: Loaded '{song}' from '{game}' ({system}) by '{author}'. Duration: {self._duration_ms} ms.")
            
            self._gme.gme_free_info(info_ptr)
        else:
            self._duration_ms = 150000

    def generate_samples(self, frame_count: int) -> np.ndarray:
        if not self._loaded or not self._emu:
            return np.zeros((frame_count, 2), dtype=np.float32)
            
        sample_count = frame_count * 2
        buffer = (ctypes.c_short * sample_count)()
        
        err = self._gme.gme_play(self._emu, sample_count, buffer)
        if err:
            err_msg = err.decode('utf-8', 'ignore') if isinstance(err, bytes) else str(err)
            print(f"GmeBackend Error: gme_play failed: {err_msg}", file=sys.stderr)
            return np.zeros((frame_count, 2), dtype=np.float32)
            
        samples_int16 = np.frombuffer(buffer, dtype=np.int16)
        samples_float32 = samples_int16.astype(np.float32) / 32768.0
        samples_stereo = samples_float32.reshape(-1, 2)
        
        if self._volume != 1.0:
            samples_stereo *= self._volume
            
        return samples_stereo

    def seek(self, position_ms: int) -> bool:
        if not self._loaded or not self._emu:
            return False
            
        err = self._gme.gme_seek(self._emu, int(position_ms))
        if err:
            err_msg = err.decode('utf-8', 'ignore') if isinstance(err, bytes) else str(err)
            print(f"GmeBackend Error: gme_seek failed: {err_msg}", file=sys.stderr)
            return False
            
        return True

    def get_duration_ms(self) -> int:
        return self._duration_ms

    def get_position_ms(self) -> int:
        if not self._loaded or not self._emu:
            return 0
        return self._gme.gme_tell(self._emu)

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, float(volume)))

    def set_channel_mute(self, channel: int, mute: bool) -> bool:
        if not self._loaded or not self._emu:
            return False
        
        voice_count = self._gme.gme_voice_count(self._emu)
        if 0 <= channel < voice_count:
            self._gme.gme_mute_voice(self._emu, int(channel), 1 if mute else 0)
            return True
        return False

    def close(self):
        if self._emu:
            self._gme.gme_delete(self._emu)
            self._emu = None
        self._loaded = False
        self._duration_ms = -1

    def is_loaded(self) -> bool:
        return self._loaded

    def __del__(self):
        try:
            self.close()
        except:
            pass
