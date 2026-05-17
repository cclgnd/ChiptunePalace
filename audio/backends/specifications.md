# backends/SPECIFICATION.md — Strict Backend Contract

All emulator backends in this folder MUST follow this exact interface.

## Base Class (base.py)
Create EmulatorBackend as an abstract base class with these methods:

```python
def load(self, data: bytes | str, filename: str = "") -> bool
def generate_samples(self, frame_count: int) -> np.ndarray  # float32, shape (frame_count, 2) stereo
def seek(self, position_ms: int) -> bool
def get_duration_ms(self) -> int
def get_position_ms(self) -> int
def set_volume(self, volume: float)  # 0.0-1.0
def set_channel_mute(self, channel: int, mute: bool) -> bool
def close(self)
def is_loaded(self) -> bool