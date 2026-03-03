import threading
import logging
import os
from kivy.utils import platform

logger = logging.getLogger(__name__)

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

HAS_SDL2_AUDIO = False
try:
    from blescanner.utils.sdl_audio import SDLAudioRecorder
    HAS_SDL2_AUDIO = True
except Exception:
    HAS_SDL2_AUDIO = False

class PyAudioRecorder:
    """Wrapper for PyAudio stream to match the recorder interface."""
    def __init__(self, rate=44100, frames_per_buffer=1024, channels=1, callback=None):
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self.channels = channels
        self.callback = callback
        self.stream = None
        self.pa = None

    def start(self):
        if self.stream:
            return
        self.pa = AudioManager.get_pyaudio()
        if not self.pa:
            raise RuntimeError("PyAudio not available")

        self.stream = self.pa.open(
            format=pyaudio.paFloat32,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.frames_per_buffer,
            stream_callback=self.callback
        )

    def stop(self):
        if self.stream:
            try:
                if self.stream.is_active():
                    self.stream.stop_stream()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
        self.pa = None

class AudioManager:
    _pa = None
    _lock = threading.Lock()
    _init_lock = threading.Lock()
    _initializing = False

    @classmethod
    def has_audio(cls):
        """Returns True if any audio backend is available."""
        if platform == 'android':
            return True
        return HAS_SDL2_AUDIO or HAS_PYAUDIO

    @classmethod
    def get_recorder(cls, rate=44100, frames_per_buffer=1024, channels=1, callback=None):
        """Returns a recorder instance for the current platform."""
        if platform == 'android':
            try:
                from blescanner.platform.android_audio import AndroidAudioRecorder
                return AndroidAudioRecorder(rate=rate, frames_per_buffer=frames_per_buffer, callback=callback)
            except Exception as e:
                logger.error(f"Failed to create AndroidAudioRecorder: {e}")
                return None

        # Prefer SDL2 for better compatibility
        if HAS_SDL2_AUDIO:
            try:
                return SDLAudioRecorder(rate=rate, frames_per_buffer=frames_per_buffer, channels=channels, callback=callback)
            except Exception as e:
                logger.warning(f"Failed to create SDL2 recorder: {e}. Falling back...")

        # Fallback to PyAudio
        if HAS_PYAUDIO:
            try:
                return PyAudioRecorder(rate=rate, frames_per_buffer=frames_per_buffer, channels=channels, callback=callback)
            except Exception as e:
                logger.error(f"Failed to create PyAudio recorder: {e}")

        return None

    @classmethod
    def is_ready(cls):
        """Returns True if PyAudio is initialized (kept for backward compatibility)."""
        if HAS_SDL2_AUDIO:
            return True
        with cls._lock:
            return cls._pa is not None

    @classmethod
    def get_pyaudio(cls, block=True):
        """
        Returns the PyAudio singleton. (Kept for backward compatibility)
        """
        if not HAS_PYAUDIO:
            return None

        # Fast path
        with cls._lock:
            if cls._pa is not None:
                return cls._pa
            if not block and cls._initializing:
                return None

        # Safe initialization
        if not block:
            if not cls._init_lock.acquire(blocking=False):
                return None
            try:
                return cls._do_guarded_init()
            finally:
                cls._init_lock.release()
        else:
            with cls._init_lock:
                return cls._do_guarded_init()

    @classmethod
    def _do_guarded_init(cls):
        with cls._lock:
            if cls._pa is not None:
                return cls._pa

        try:
            logger.info("Initializing PyAudio singleton...")
            pa = pyaudio.PyAudio()
            with cls._lock:
                cls._pa = pa
            logger.info("PyAudio initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")

        return cls._pa

    @classmethod
    def start_initialization(cls):
        """Starts audio initialization in a background thread."""
        if HAS_SDL2_AUDIO:
             # SDL2 initialization is handled in SDLAudioRecorder
             return

        if not HAS_PYAUDIO:
            return

        with cls._lock:
            if cls._pa is not None or cls._initializing:
                return
            cls._initializing = True

        def _do_bg_init():
            try:
                cls.get_pyaudio()
            finally:
                with cls._lock:
                    cls._initializing = False

        threading.Thread(target=_do_bg_init, daemon=True).start()

    @classmethod
    def terminate(cls):
        """Terminates audio backends."""
        def _bg_terminate():
            with cls._init_lock:
                with cls._lock:
                    if cls._pa:
                        try:
                            cls._pa.terminate()
                            logger.info("PyAudio terminated.")
                        except Exception as e:
                            logger.error(f"Error terminating PyAudio: {e}")
                        cls._pa = None

        threading.Thread(target=_bg_terminate, daemon=True).start()
