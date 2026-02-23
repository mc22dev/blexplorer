import numpy as np
import threading
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
        try:
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
        return (None, pyaudio.paContinue)

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
