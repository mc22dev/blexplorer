import ctypes
import os
import logging
import threading
import numpy as np

logger = logging.getLogger(__name__)

# SDL2 Constants
SDL_INIT_AUDIO = 0x00000010
AUDIO_F32 = 0x8120

class SDL_AudioSpec(ctypes.Structure):
    _fields_ = [
        ("freq", ctypes.c_int),
        ("format", ctypes.c_uint16),
        ("channels", ctypes.c_uint8),
        ("silence", ctypes.c_uint8),
        ("samples", ctypes.c_uint16),
        ("padding", ctypes.c_uint16),
        ("size", ctypes.c_uint32),
        ("callback", ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint8), ctypes.c_int)),
        ("userdata", ctypes.c_void_p),
    ]

class SDLAudioRecorder:
    _sdl2 = None
    _lib_lock = threading.Lock()

    def __init__(self, rate=44100, frames_per_buffer=1024, channels=1, callback=None):
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self.channels = channels
        self.user_callback = callback
        self.device_id = 0
        self.is_running = False

        self._load_sdl2()

    def _load_sdl2(self):
        with SDLAudioRecorder._lib_lock:
            if SDLAudioRecorder._sdl2:
                return

            try:
                sdl2 = None
                if os.name == 'nt':
                    sdl2 = ctypes.cdll.LoadLibrary('SDL2.dll')
                elif os.name == 'posix':
                    # Try common names for Linux/macOS
                    for name in ['libSDL2-2.0.so.0', 'libSDL2.so', 'SDL2', '/usr/local/lib/libSDL2.dylib']:
                        try:
                            sdl2 = ctypes.cdll.LoadLibrary(name)
                            if sdl2: break
                        except OSError:
                            continue

                if not sdl2:
                    raise RuntimeError("SDL2 library not found")

                # Setup return types
                sdl2.SDL_GetError.restype = ctypes.c_char_p
                sdl2.SDL_OpenAudioDevice.restype = ctypes.c_uint32
                sdl2.SDL_GetAudioDeviceName.restype = ctypes.c_char_p

                SDLAudioRecorder._sdl2 = sdl2

                if sdl2.SDL_Init(SDL_INIT_AUDIO) != 0:
                    error = sdl2.SDL_GetError().decode()
                    SDLAudioRecorder._sdl2 = None
                    raise RuntimeError(f"SDL_Init Error: {error}")

                logger.info("SDL2 Audio initialized")
            except Exception as e:
                logger.error(f"Failed to load SDL2: {e}")
                raise

    def _audio_callback(self, userdata, stream_ptr, length):
        if not self.is_running or not self.user_callback:
            return

        # stream_ptr is a pointer to the audio data
        # length is in bytes

        # Convert to numpy array efficiently
        # AUDIO_F32 is 4 bytes per sample
        num_samples = length // 4
        # Create a buffer from the pointer
        buffer = ctypes.string_at(stream_ptr, length)

        # In SDL2 capture mode, we should pass the data to the user callback
        # The user callback expects (in_data, frame_count, time_info, status)
        # matching pyaudio's signature for easier transition.

        # Calculate frame count (samples per channel)
        frame_count = num_samples // self.channels

        try:
            self.user_callback(buffer, frame_count, None, 0)
        except Exception as e:
            logger.error(f"Error in SDL audio callback: {e}")

    def start(self):
        if self.is_running:
            return

        sdl2 = SDLAudioRecorder._sdl2
        if not sdl2:
            raise RuntimeError("SDL2 not initialized")

        desired = SDL_AudioSpec()
        desired.freq = self.rate
        desired.format = AUDIO_F32
        desired.channels = self.channels
        desired.samples = self.frames_per_buffer

        # Keep a reference to the callback to prevent GC
        self._c_callback = SDL_AudioSpec._fields_[7][1](self._audio_callback)
        desired.callback = self._c_callback
        desired.userdata = None

        obtained = SDL_AudioSpec()

        # SDL_OpenAudioDevice(const char* device, int iscapture, const SDL_AudioSpec* desired, SDL_AudioSpec* obtained, int allowed_changes)
        self.device_id = sdl2.SDL_OpenAudioDevice(None, 1, ctypes.byref(desired), ctypes.byref(obtained), 0)

        if self.device_id == 0:
            error = sdl2.SDL_GetError().decode()
            raise RuntimeError(f"SDL_OpenAudioDevice Error: {error}")

        logger.info(f"Opened SDL audio capture device {self.device_id}")

        self.is_running = True
        sdl2.SDL_PauseAudioDevice(self.device_id, 0) # Start recording

    def stop(self):
        if not self.is_running:
            return

        self.is_running = False
        sdl2 = SDLAudioRecorder._sdl2
        if sdl2 and self.device_id != 0:
            sdl2.SDL_PauseAudioDevice(self.device_id, 1)
            sdl2.SDL_CloseAudioDevice(self.device_id)
            self.device_id = 0

    def __del__(self):
        self.stop()
