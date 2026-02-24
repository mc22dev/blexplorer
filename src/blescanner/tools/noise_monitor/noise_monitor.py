import numpy as np
import threading
import time
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty, StringProperty, NumericProperty
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
import os

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, cast
    AudioRecord = autoclass('android.media.AudioRecord')
    AudioSource = autoclass('android.media.MediaRecorder$AudioSource')
    AudioFormat = autoclass('android.media.AudioFormat')
    ByteBuffer = autoclass('java.nio.ByteBuffer')
    HAS_PYAUDIO = True # We have alternative for Android

class AndroidAudioRecorder:
    def __init__(self, rate=44100, frames_per_buffer=1024, callback=None):
        self.rate = rate
        self.frames_per_buffer = frames_per_buffer
        self.callback = callback
        self.is_running = False
        self._thread = None

        # Configure AudioRecord using PCM_16BIT for maximum compatibility
        self.channels = AudioFormat.CHANNEL_IN_MONO
        self.format = AudioFormat.ENCODING_PCM_16BIT
        self.buffer_size = AudioRecord.getMinBufferSize(rate, self.channels, self.format)

        self.recorder = AudioRecord(
            AudioSource.MIC,
            self.rate,
            self.channels,
            self.format,
            max(self.buffer_size, self.frames_per_buffer * 2)
        )

    def start(self):
        if self.recorder.getState() != AudioRecord.STATE_INITIALIZED:
            raise Exception("AudioRecord failed to initialize")
        self.recorder.startRecording()
        self.is_running = True
        self._thread = threading.Thread(target=self._read_loop)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self.is_running = False
        if self.recorder:
            try:
                self.recorder.stop()
                self.recorder.release()
            except:
                pass

    def _read_loop(self):
        try:
            # We use a direct ByteBuffer to ensure we can read from the AudioRecord
            # efficiently even if jarray is missing.
            j_buffer = ByteBuffer.allocateDirect(self.frames_per_buffer * 2)
            j_buffer.order(autoclass('java.nio.ByteOrder').nativeOrder())

            while self.is_running:
                j_buffer.clear()
                # read(ByteBuffer audioBuffer, int sizeInBytes) - Added in API 3
                result_bytes = self.recorder.read(j_buffer, self.frames_per_buffer * 2)

                if result_bytes > 0:
                    # Move to start of buffer to read data out
                    j_buffer.position(0)

                    # Read shorts from the ByteBuffer into a numpy array
                    # This is a bit slower than a direct copy but robust without jarray.
                    shorts_to_read = result_bytes // 2
                    short_data = np.zeros(shorts_to_read, dtype=np.int16)
                    for i in range(shorts_to_read):
                        short_data[i] = j_buffer.getShort()

                    float_data = short_data.astype(np.float32) / 32768.0

                    if self.callback:
                        self.callback(float_data.tobytes(), shorts_to_read, None, None)
                elif result_bytes < 0:
                    # Error code returned by AudioRecord
                    time.sleep(0.1)
                else:
                    # No data available, wait a bit
                    time.sleep(0.01)
        except Exception as e:
            print(f"NoiseMonitor: Error in Android read loop: {e}")

class NoiseBarGraph(Widget):
    """
    A bar graph widget that displays 9 blocks.
    3 Green, 3 Orange, 3 Red.
    """
    level = NumericProperty(0) # 0 to 9

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_graph, size=self.update_graph, level=self.update_graph)

    def update_graph(self, *args):
        self.canvas.clear()
        with self.canvas:
            w = self.width
            h = self.height
            x0 = self.x
            y0 = self.y

            block_spacing = 5
            total_blocks = 9
            block_height = (h - (total_blocks - 1) * block_spacing) / total_blocks

            for i in range(total_blocks):
                # Blocks are drawn from bottom to top
                if i < 3:
                    color = (0, 1, 0, 1) # Green
                elif i < 6:
                    color = (1, 0.5, 0, 1) # Orange
                else:
                    color = (1, 0, 0, 1) # Red

                if i < self.level:
                    opacity = 1.0
                else:
                    opacity = 0.2

                Color(*color[:3], opacity)
                Rectangle(pos=(x0, y0 + i * (block_height + block_spacing)),
                          size=(w, block_height))

class NoiseMonitorScreen(Screen):
    noise_level = NumericProperty(0)
    is_running = BooleanProperty(False)
    status_text = StringProperty("Stopped")
    has_pyaudio = BooleanProperty(HAS_PYAUDIO)
    sensitivity = NumericProperty(1.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio = None
        self.stream = None
        self.android_recorder = None
        self._lock = threading.Lock()
        self._new_data = False
        self._buffer = np.zeros(1024)
        self.alert_sound = None
        self._last_alert_time = 0

    def on_enter(self):
        if not self.alert_sound:
            try:
                # Use App's resource_path if available
                from kivy.app import App
                app = App.get_running_app()
                if hasattr(app, 'user_data_dir'): # Check if it's the real app
                     # We can't easily import resource_path from __main__ here due to circular imports
                     # But we know where it is relative to this file
                     current_dir = os.path.dirname(__file__)
                     # src/blescanner/tools/noise_monitor -> src/blescanner/assets/sounds/alert.wav
                     sound_path = os.path.join(current_dir, "..", "..", "assets", "sounds", "alert.wav")
                     sound_path = os.path.abspath(sound_path)
                     self.alert_sound = SoundLoader.load(sound_path)
            except Exception as e:
                print(f"Error loading sound: {e}")

    def toggle_running(self):
        if self.is_running:
            self.stop_audio()
        else:
            self.start_audio()

    def start_audio(self):
        if self.is_running or not HAS_PYAUDIO:
            return

        if platform == 'android':
            from android.permissions import request_permissions, Permission
            def callback(permissions, grants):
                if all(grants):
                    self._do_start_audio()
                else:
                    self.status_text = "Permission denied"
            request_permissions([Permission.RECORD_AUDIO], callback)
        else:
            self._do_start_audio()

    def _do_start_audio(self):
        try:
            if platform == 'android':
                self.android_recorder = AndroidAudioRecorder(callback=self._audio_callback)
                self.android_recorder.start()
            else:
                self.audio = pyaudio.PyAudio()
                self.stream = self.audio.open(
                    format=pyaudio.paFloat32,
                    channels=1,
                    rate=44100,
                    input=True,
                    frames_per_buffer=1024,
                    stream_callback=self._audio_callback
                )
            self.is_running = True
            self.status_text = "Monitoring noise..."
            Clock.schedule_interval(self.update_noise_level, 1.0 / 20.0)
        except Exception as e:
            self.status_text = f"Error: {e}"
            if self.audio:
                self.audio.terminate()
            self.audio = None

    def stop_audio(self):
        self.is_running = False
        self.status_text = "Stopped"
        Clock.unschedule(self.update_noise_level)
        if platform == 'android':
            if self.android_recorder:
                self.android_recorder.stop()
                self.android_recorder = None
        else:
            if self.stream:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except:
                    pass
                self.stream = None
            if self.audio:
                try:
                    self.audio.terminate()
                except:
                    pass
                self.audio = None

    def _audio_callback(self, in_data, frame_count, time_info, status):
        data = np.frombuffer(in_data, dtype=np.float32)
        with self._lock:
            self._buffer = data
            self._new_data = True
        # Return 0 (equivalent to pyaudio.paContinue)
        return (None, 0)

    def update_noise_level(self, dt):
        if not self._new_data:
            return

        with self._lock:
            data = self._buffer.copy()
            self._new_data = False

        if len(data) == 0:
            return

        # Calculate RMS
        rms = np.sqrt(np.mean(data**2))

        # Map RMS to 0-9 scale.
        # Sensitivity 1.0 means RMS of 0.1 is level 9.
        target_level = float(rms * 90 * self.sensitivity)

        # Simple smoothing (EMA)
        self.noise_level = float(self.noise_level * 0.5 + min(9.0, target_level) * 0.5)

        if self.noise_level >= 7: # Red zone (7, 8, 9)
            self.trigger_alert()

    def trigger_alert(self):
        now = Clock.get_time()
        if now - self._last_alert_time > 2.0: # 2 seconds cooldown
            if self.alert_sound:
                self.alert_sound.play()
            self._last_alert_time = now

    def on_leave(self, *args):
        self.stop_audio()
