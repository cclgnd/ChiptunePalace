from abc import ABC, abstractmethod
import numpy as np

class EmulatorBackend(ABC):
    """
    Abstract base class for all real-time audio emulation backends.
    All emulators MUST implement this contract exactly.
    """
    
    @abstractmethod
    def load(self, data: bytes | str, filename: str = "") -> bool:
        """
        Loads the music track from raw bytes or a file path.
        Returns True if loading was successful, False otherwise.
        """
        pass
        
    @abstractmethod
    def generate_samples(self, frame_count: int) -> np.ndarray:
        """
        Synthesizes the next 'frame_count' stereo sample frames.
        Returns a float32 numpy array with shape (frame_count, 2) and values in range [-1.0, 1.0].
        """
        pass
        
    @abstractmethod
    def seek(self, position_ms: int) -> bool:
        """
        Seeks to the given playback position in milliseconds.
        Returns True on success, False otherwise.
        """
        pass
        
    @abstractmethod
    def get_duration_ms(self) -> int:
        """
        Returns the duration of the current track in milliseconds.
        Returns -1 or a standard default (e.g. 150000) if the duration is unknown/infinite loop.
        """
        pass
        
    @abstractmethod
    def get_position_ms(self) -> int:
        """
        Returns the current playback position in milliseconds.
        """
        pass
        
    @abstractmethod
    def set_volume(self, volume: float):
        """
        Sets the player volume from 0.0 (silent) to 1.0 (max volume).
        """
        pass
        
    @abstractmethod
    def set_channel_mute(self, channel: int, mute: bool) -> bool:
        """
        Mutes or unmutes a specific emulation voice channel.
        Returns True if successful/supported, False otherwise.
        """
        pass
        
    @abstractmethod
    def close(self):
        """
        Closes the active emulator and releases any native/allocated resources.
        """
        pass
        
    @abstractmethod
    def is_loaded(self) -> bool:
        """
        Returns True if a track is successfully loaded, False otherwise.
        """
        pass
