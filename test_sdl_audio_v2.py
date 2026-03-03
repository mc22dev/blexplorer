import ctypes
import os

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

def main():
    try:
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

        sdl2.SDL_GetError.restype = ctypes.c_char_p
        sdl2.SDL_OpenAudioDevice.restype = ctypes.c_uint32

        if sdl2.SDL_Init(SDL_INIT_AUDIO) != 0:
            print(f"SDL_Init Error: {sdl2.SDL_GetError().decode()}")
            return

        print("SDL Audio initialized")

        # Check if we can list recording devices
        sdl2.SDL_GetNumAudioDevices.restype = ctypes.c_int
        sdl2.SDL_GetAudioDeviceName.restype = ctypes.c_char_p

        num_capture = sdl2.SDL_GetNumAudioDevices(1)
        print(f"Number of capture devices: {num_capture}")
        for i in range(num_capture):
            name = sdl2.SDL_GetAudioDeviceName(i, 1)
            print(f"  [{i}] {name.decode() if name else 'Unknown'}")

        sdl2.SDL_Quit()
        print("Done")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
