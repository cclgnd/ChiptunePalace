import sys
import numpy as np
import sounddevice as sd
from PySide6.QtCore import QObject, Signal

class SoundDeviceOutput(QObject):
    # Standard PySide6 signals
    playback_state_changed = Signal(str)
    position_changed = Signal(int)  # in milliseconds
    duration_changed = Signal(int)  # in milliseconds
    track_finished = Signal()
    error_occurred = Signal(str)
    warning_occurred = Signal(str)

    def __init__(self, sample_rate: int = 44100):
        super().__init__()
        self.sample_rate = sample_rate
        self._stream = None
        self._backend = None
        self._state = "Stopped"
        self._last_emitted_pos_ms = -1
        self._volume = 0.8

    def set_backend(self, backend):
        """Sets the active emulator backend."""
        self.stop()
        self._backend = backend
        if backend:
            backend.set_volume(self._volume)
            # Emit duration
            dur = backend.get_duration_ms()
            self.duration_changed.emit(dur)
            self.position_changed.emit(0)

    def play(self) -> bool:
        if not self._backend:
            self.error_occurred.emit("No backend loaded")
            return False

        if self._state == "Playing":
            return True

        try:
            # If stream exists, just start it, else construct it
            if self._stream is None:
                self._stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=2,
                    dtype='float32',
                    blocksize=512,  # low-latency
                    callback=self._audio_callback
                )
                self._stream.start()
            else:
                self._stream.start()

            self._state = "Playing"
            self.playback_state_changed.emit(self._state)
            return True
        except Exception as e:
            msg = f"Failed to start sounddevice stream: {e}"
            print(msg, file=sys.stderr)
            self.error_occurred.emit(msg)
            self.stop()
            return False

    def pause(self):
        if self._state != "Playing":
            return

        try:
            if self._stream:
                self._stream.stop()
            self._state = "Paused"
            self.playback_state_changed.emit(self._state)
        except Exception as e:
            self.warning_occurred.emit(f"Failed to pause stream: {e}")

    def stop(self):
        self._state = "Stopped"
        try:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
        except Exception as e:
            self.warning_occurred.emit(f"Failed to stop/close stream: {e}")
        finally:
            self.playback_state_changed.emit("Stopped")
            self._last_emitted_pos_ms = -1

    def set_volume(self, volume: float):
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._backend:
            self._backend.set_volume(self._volume)

    def get_state(self) -> str:
        return self._state

    def _audio_callback(self, outdata, frames, time, status):
        if status:
            # Send warning but do not crash the thread
            self.warning_occurred.emit(f"sounddevice status: {status}")

        if not self._backend or self._state != "Playing":
            outdata.fill(0)
            return

        # Fetch synthesized samples
        samples = self._backend.generate_samples(frames)

        # Handle end of track or buffer underrun
        if len(samples) < frames:
            outdata[:len(samples)] = samples
            outdata[len(samples):].fill(0)
            self._state = "Stopped"
            self.track_finished.emit()
            return
        else:
            outdata[:] = samples

        # Manage position notifications
        pos_ms = self._backend.get_position_ms()
        dur_ms = self._backend.get_duration_ms()

        # Stop playback if we reached the duration limit
        if dur_ms > 0 and pos_ms >= dur_ms:
            outdata.fill(0)
            self._state = "Stopped"
            self.track_finished.emit()
            return

        # Throttle position signals to avoid GUI thread blockages
        if abs(pos_ms - self._last_emitted_pos_ms) >= 250:
            self._last_emitted_pos_ms = pos_ms
            self.position_changed.emit(pos_ms)

    def close(self):
        self.stop()
        self._backend = None

    def __del__(self):
        try:
            self.close()
        except:
            pass
