import ctypes
import time

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

def audio_callback(userdata, stream, length):
    print(f"Received {length} bytes of audio data")

def main():
    try:
        import os
        sdl2 = None
        if os.name == 'nt':
            sdl2 = ctypes.cdll.LoadLibrary('SDL2.dll')
        elif os.name == 'posix':
            try:
                sdl2 = ctypes.cdll.LoadLibrary('libSDL2-2.0.so.0')
            except OSError:
                sdl2 = ctypes.cdll.LoadLibrary('libSDL2.so')

        if not sdl2:
            print("SDL2 library not found")
            return

        if sdl2.SDL_Init(SDL_INIT_AUDIO) != 0:
            print(f"SDL_Init Error: {sdl2.SDL_GetError()}")
            return

        desired = SDL_AudioSpec()
        desired.freq = 44100
        desired.format = AUDIO_F32
        desired.channels = 1
        desired.samples = 1024
        desired.callback = SDL_AudioSpec._fields_[7][1](audio_callback)
        desired.userdata = None

        obtained = SDL_AudioSpec()

        # SDL_OpenAudioDevice(const char* device, int iscapture, const SDL_AudioSpec* desired, SDL_AudioSpec* obtained, int allowed_changes)
        device_id = sdl2.SDL_OpenAudioDevice(None, 1, ctypes.byref(desired), ctypes.byref(obtained), 0)

        if device_id == 0:
            print(f"SDL_OpenAudioDevice Error: {sdl2.SDL_GetError().decode()}")
            return

        print(f"Opened audio device {device_id}")
        print(f"Obtained spec: freq={obtained.freq}, format={obtained.format:x}, channels={obtained.channels}, samples={obtained.samples}")

        sdl2.SDL_PauseAudioDevice(device_id, 0)

        time.sleep(2)

        sdl2.SDL_CloseAudioDevice(device_id)
        sdl2.SDL_Quit()
        print("Success")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
