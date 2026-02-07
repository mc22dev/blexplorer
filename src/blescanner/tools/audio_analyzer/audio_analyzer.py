import numpy as np
import math
import threading
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.properties import ListProperty, BooleanProperty, StringProperty, NumericProperty, ObjectProperty
from kivy.graphics import Color, Line, Rectangle
from kivy.clock import Clock
from kivy.utils import platform as kivy_platform

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False

class SpectrumGraph(Widget):
    magnitude_data = ListProperty([])
    frequencies = ListProperty([])
    is_log_x = BooleanProperty(True)
    is_log_y = BooleanProperty(True)
    min_db = NumericProperty(-100)
    max_db = NumericProperty(0)
    min_freq = NumericProperty(20)
    max_freq = NumericProperty(20000)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_graph, size=self.update_graph, magnitude_data=self.update_graph)

    def update_graph(self, *args):
        self.canvas.after.clear()
        if not self.magnitude_data or not self.frequencies:
            return

        with self.canvas.after:
            Color(0, 1, 0, 1)  # Green for the spectrum

            w = self.width
            h = self.height
            x0 = self.x
            y0 = self.y

            mags = np.array(self.magnitude_data)
            freqs = np.array(self.frequencies)

            # Filter frequencies
            mask = (freqs >= self.min_freq) & (freqs <= self.max_freq)
            f_filtered = freqs[mask]
            m_filtered = mags[mask]

            if len(f_filtered) < 2:
                return

            # Magnitude to Y
            if self.is_log_y:
                # Convert magnitude to dB
                db = 20 * np.log10(np.maximum(m_filtered, 1e-10))
                # Normalize dB to 0-1 range
                norm_y = (db - self.min_db) / (self.max_db - self.min_db)
            else:
                # Linear scale normalized to 0-1 (assuming max magnitude is 1.0)
                norm_y = m_filtered

            norm_y = np.clip(norm_y, 0, 1)

            # Frequency to X
            if self.is_log_x:
                min_log_f = math.log10(max(self.min_freq, 1))
                max_log_f = math.log10(max(self.max_freq, 1))
                norm_x = (np.log10(np.maximum(f_filtered, 1e-10)) - min_log_f) / (max_log_f - min_log_f)
            else:
                norm_x = (f_filtered - self.min_freq) / (self.max_freq - self.min_freq)

            norm_x = np.clip(norm_x, 0, 1)

            # Create points list efficiently
            points = np.empty(len(norm_x) * 2)
            points[0::2] = x0 + norm_x * w
            points[1::2] = y0 + norm_y * h

            Line(points=points.tolist(), width=1.5)

            # Draw grid
            Color(1, 1, 1, 0.2)
            # Frequencies grid (Vertical lines)
            freq_labels = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000]
            if self.is_log_x:
                min_log_f = math.log10(max(self.min_freq, 1))
                max_log_f = math.log10(max(self.max_freq, 1))
                for f in freq_labels:
                    if f < self.min_freq or f > self.max_freq:
                        continue
                    nx = (math.log10(f) - min_log_f) / (max_log_f - min_log_f)
                    Line(points=[x0 + nx * w, y0, x0 + nx * w, y0 + h], width=1)
            else:
                for f in freq_labels:
                    if f < self.min_freq or f > self.max_freq:
                        continue
                    nx = (f - self.min_freq) / (self.max_freq - self.min_freq)
                    Line(points=[x0 + nx * w, y0, x0 + nx * w, y0 + h], width=1)

            # dB grid (Horizontal lines)
            if self.is_log_y:
                db_labels = [-80, -60, -40, -20]
                for db in db_labels:
                    ny = (db - self.min_db) / (self.max_db - self.min_db)
                    Line(points=[x0, y0 + ny * h, x0 + w, y0 + ny * h], width=1)
            else:
                mag_labels = [0.25, 0.5, 0.75]
                for m in mag_labels:
                    Line(points=[x0, y0 + m * h, x0 + w, y0 + m * h], width=1)

class AudioAnalyzerScreen(Screen):
    magnitude_data = ListProperty([])
    frequencies = ListProperty([])
    is_running = BooleanProperty(False)
    peak_freq_text = StringProperty("N/A")
    fps_text = StringProperty("0")
    status_text = StringProperty("")

    RATE = 44100
    CHUNK = 2048

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.audio = None
        self.stream = None
        self._last_time = Clock.get_time()
        self._frame_count = 0
        self._lock = threading.Lock()
        self._new_data = False
        self._buffer = np.zeros(self.CHUNK)
        if not HAS_PYAUDIO:
            self.status_text = "PyAudio not found. Audio capture is unavailable."

    def toggle_running(self):
        if self.is_running:
            self.stop_audio()
        else:
            self.start_audio()

    def start_audio(self):
        if self.is_running:
            return

        if not HAS_PYAUDIO:
            self.status_text = "PyAudio not found."
            return

        try:
            self.audio = pyaudio.PyAudio()
            self.stream = self.audio.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK,
                stream_callback=self._audio_callback
            )
            self.is_running = True
            self.status_text = "Capturing audio..."
            Clock.schedule_interval(self.update_ui, 1.0 / 30.0)
        except Exception as e:
            self.status_text = f"Error: {e}"
            if self.audio:
                self.audio.terminate()
            self.audio = None

    def stop_audio(self):
        self.is_running = False
        self.status_text = "Stopped."
        Clock.unschedule(self.update_ui)
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

    def update_ui(self, dt):
        if not self._new_data:
            return

        with self._lock:
            data = self._buffer.copy()
            self._new_data = False

        if len(data) == 0:
            return

        # Apply window function
        window = np.hanning(len(data))
        windowed_data = data * window

        # FFT
        fft_res = np.fft.rfft(windowed_data)
        magnitudes = np.abs(fft_res) / (len(data) / 2)
        freqs = np.fft.rfftfreq(len(data), 1.0 / self.RATE)

        # Update properties (triggers UI update)
        self.magnitude_data = magnitudes.tolist()
        self.frequencies = freqs.tolist()

        # Peak detection
        peak_idx = np.argmax(magnitudes)
        peak_freq = freqs[peak_idx]
        self.peak_freq_text = f"{peak_freq:.1f} Hz"

        # FPS calculation
        self._frame_count += 1
        now = Clock.get_time()
        if now - self._last_time >= 1.0:
            self.fps_text = str(self._frame_count)
            self._frame_count = 0
            self._last_time = now

    def on_leave(self, *args):
        self.stop_audio()
