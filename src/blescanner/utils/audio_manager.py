import threading
import logging

logger = logging.getLogger(__name__)

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

class AudioManager:
    _pa = None
    _lock = threading.Lock()
    _init_lock = threading.Lock()
    _initializing = False

    @classmethod
    def is_ready(cls):
        """Returns True if PyAudio is initialized."""
        with cls._lock:
            return cls._pa is not None

    @classmethod
    def get_pyaudio(cls, block=True):
        """
        Returns the PyAudio singleton.

        Args:
            block: If True, blocks until initialization is complete if currently initializing.
                   If False, returns None immediately if not ready.
        """
        if not HAS_PYAUDIO:
            return None

        # Fast path
        with cls._lock:
            if cls._pa is not None:
                return cls._pa
            if not block and cls._initializing:
                return None

        # Safe initialization with its own lock to avoid blocking _lock for too long
        # and to prevent multiple simultaneous PyAudio() calls.
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
        # Check again after acquiring init_lock
        with cls._lock:
            if cls._pa is not None:
                return cls._pa

        try:
            logger.info("Initializing PyAudio singleton (may block for several seconds)...")
            pa = pyaudio.PyAudio()
            with cls._lock:
                cls._pa = pa
            logger.info("PyAudio initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")

        return cls._pa

    @classmethod
    def start_initialization(cls):
        """Starts PyAudio initialization in a background thread."""
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
        """Terminates the PyAudio singleton."""
        # Use a thread for termination too, as it can block
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
