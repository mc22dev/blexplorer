import numpy as np
import threading
import time
from collections import deque
from kivy.uix.screenmanager import Screen
from kivy.uix.widget import Widget
from kivy.properties import BooleanProperty, StringProperty, NumericProperty
from kivy.graphics import Color, Rectangle
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.factory import Factory
import os
import sys
from blescanner.models import LogLevel
from blescanner.utils.audio_manager import AudioManager

from kivy.utils import platform

HAS_AUDIO = AudioManager.has_audio()

class NoiseBarGraph(Widget):
    """
    A bar graph widget that displays a configurable number of blocks.
    Split into Green, Orange, and Red zones.
    """
    level = NumericProperty(0)
    num_bars = NumericProperty(9)
    paused = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_graph, size=self.update_graph, level=self.update_graph, num_bars=self.update_graph, paused=self.update_graph)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self.paused = not self.paused
            return True
        return super().on_touch_down(touch)

    def update_graph(self, *args):
        self.canvas.clear()
        with self.canvas:
            w = self.width
            h = self.height
            x0 = self.x
            y0 = self.y

            block_spacing = 5
            total_blocks = int(self.num_bars)
            if total_blocks < 1: total_blocks = 1
            block_height = (h - (total_blocks - 1) * block_spacing) / total_blocks

            for i in range(total_blocks):
                # Blocks are drawn from bottom to top
                # Dynamic color zones
                if i < total_blocks / 3.0:
                    color = (0, 1, 0, 1) # Green
                elif i < 2.0 * total_blocks / 3.0:
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

            if self.paused:
                Color(1, 1, 1, 0.8)
                # Draw two vertical bars in the center for the pause icon
                icon_w = w * 0.1
                icon_h = h * 0.3
                cx = self.center_x
                cy = self.center_y
                # Left bar
                Rectangle(pos=(cx - icon_w * 1.2, cy - icon_h / 2),
                          size=(icon_w, icon_h))
                # Right bar
                Rectangle(pos=(cx + icon_w * 0.2, cy - icon_h / 2),
                          size=(icon_w, icon_h))

class NoiseMonitorScreen(Screen):
    noise_level = NumericProperty(0)
    is_running = BooleanProperty(False)
    is_paused = BooleanProperty(False)
    status_text = StringProperty("Stopped")
    has_audio = BooleanProperty(HAS_AUDIO)
    sensitivity = NumericProperty(1.0)
    num_bars = NumericProperty(9)
    average_time = NumericProperty(500) # ms
    alarm_cooldown = NumericProperty(2) # seconds

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recorder = None
        self._lock = threading.Lock()
        self._new_data = False
        self._buffer = np.zeros(1024)
        self.alert_sound = None
        self._current_sound_name = ""
        self._last_alert_time = 0
        self._rms_buffer = deque()
        self._loading_sound = False

    def on_enter(self):
        # Use schedule_once to avoid doing heavy work exactly during screen transition
        def _deferred_enter(dt):
            self.load_settings()
            self.start_audio()
        Clock.schedule_once(_deferred_enter)

    def load_settings(self):
        try:
            from kivy.app import App
            app = App.get_running_app()
            self.sensitivity = float(app.config_manager.get_setting('noise_monitor', 'sensitivity', default='1.0'))
            self.num_bars = int(app.config_manager.get_setting('noise_monitor', 'num_bars', default='9'))
            self.average_time = int(app.config_manager.get_setting('noise_monitor', 'average_time', default='500'))
            self.alarm_cooldown = int(app.config_manager.get_setting('noise_monitor', 'alarm_cooldown', default='2'))
        except:
            pass
        self.load_alarm_sound()

    def load_alarm_sound(self):
        try:
            from kivy.app import App
            app = App.get_running_app()
            sound_name = app.config_manager.get_setting('noise_monitor', 'alarm_sound')

            if sound_name == self._current_sound_name or self._loading_sound:
                return

            self._loading_sound = True

            if os.path.isabs(sound_name):
                sound_path = sound_name
            else:
                # Robust asset path logic that works on Desktop and Android
                if hasattr(sys, '_MEIPASS'):
                    base_path = os.path.join(sys._MEIPASS, 'blescanner')
                else:
                    # For development, base_path is src/blescanner/
                    # noise_monitor.py is in src/blescanner/tools/noise_monitor/
                    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

                sound_path = os.path.join(base_path, "assets", "sounds", sound_name)

            if self.alert_sound:
                old_sound = self.alert_sound
                self.alert_sound = None
                def _bg_unload():
                    try:
                        old_sound.unload()
                    except: pass
                threading.Thread(target=_bg_unload, daemon=True).start()

            if not os.path.exists(sound_path):
                app.log_with_timestamp(f"Sound file not found: {sound_path}", LogLevel.ERROR)
                self._loading_sound = False
                return

            def _do_load(dt):
                try:
                    sound = SoundLoader.load(sound_path)
                    if sound:
                        self.alert_sound = sound
                        self.alert_sound.volume = 1.0
                        self._current_sound_name = sound_name
                        app.log_with_timestamp(f"Loaded alarm sound: {sound_name}", LogLevel.INFO)
                    else:
                        app.log_with_timestamp(f"Failed to load alarm sound: {sound_name}", LogLevel.ERROR)
                except Exception as e:
                    print(f"Error loading sound: {e}")
                finally:
                    self._loading_sound = False

            Clock.schedule_once(_do_load)
        except Exception as e:
            self._loading_sound = False
            print(f"Error loading sound: {e}")

    def toggle_running(self):
        if self.is_running:
            self.stop_audio()
        else:
            self.start_audio()

    def start_audio(self):
        if self.is_running or not HAS_AUDIO:
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
        self.is_running = True
        self.status_text = "Initializing audio..."
        # Add a small delay to allow UI to update before background thread starts
        Clock.schedule_once(lambda dt: threading.Thread(target=self._bg_start_audio, daemon=True).start(), 0.1)

    def _bg_start_audio(self):
        new_recorder = None
        try:
            new_recorder = AudioManager.get_recorder(
                callback=self._audio_callback
            )

            if not new_recorder:
                raise Exception("Audio device initialization failed.")

            new_recorder.start()

            def _finish_init(dt):
                if not self.is_running:
                    # stop_audio was called during initialization
                    if new_recorder:
                        try:
                            new_recorder.stop()
                        except: pass
                    return

                self.recorder = new_recorder
                self.status_text = "Monitoring noise..."
                Clock.schedule_interval(self.update_noise_level, 1.0 / 20.0)

            Clock.schedule_once(_finish_init)
        except Exception as e:
            if new_recorder:
                try: new_recorder.stop()
                except: pass

            def _handle_error(dt):
                self.status_text = f"Error: {e}"
                self.is_running = False
            Clock.schedule_once(_handle_error)

    def stop_audio(self):
        self.is_running = False
        self.status_text = "Stopped"
        Clock.unschedule(self.update_noise_level)

        recorder = self.recorder
        self.recorder = None

        def _bg_stop():
            if recorder:
                try:
                    recorder.stop()
                except: pass

        if recorder:
            threading.Thread(target=_bg_stop, daemon=True).start()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        data = np.frombuffer(in_data, dtype=np.float32)
        with self._lock:
            self._buffer = data
            self._new_data = True

        # Use paContinue (0)
        return (None, 0)

    def update_noise_level(self, dt):
        if self.is_paused or not self._new_data:
            return

        with self._lock:
            data = self._buffer.copy()
            self._new_data = False

        if len(data) == 0:
            return

        # Calculate current RMS
        rms = np.sqrt(np.mean(data**2))

        # Maintain sliding window buffer
        # update_noise_level is called 20 times per second (dt=0.05)
        max_samples = max(1, int(self.average_time / 50))
        self._rms_buffer.append(rms)
        while len(self._rms_buffer) > max_samples:
            self._rms_buffer.popleft()

        # Calculate average RMS over the window
        avg_rms = sum(self._rms_buffer) / len(self._rms_buffer)

        # Map average RMS to 0-N scale.
        # Sensitivity 1.0 means average RMS of 0.1 is max level.
        target_level = float(avg_rms * (self.num_bars * 10) * self.sensitivity)

        # Simple smoothing (EMA) for visual stability on top of averaging
        self.noise_level = float(self.noise_level * 0.5 + min(float(self.num_bars), target_level) * 0.5)

        if self.noise_level >= self.num_bars - 0.5: # Last red bar
            self.trigger_alert()

    def trigger_alert(self):
        now = Clock.get_time()
        if now - self._last_alert_time > self.alarm_cooldown:
            try:
                from kivy.app import App
                app = App.get_running_app()
                app.log_with_timestamp("Noise alert triggered!", LogLevel.WARNING)
            except:
                pass
            if self.alert_sound:
                # Play sound in a separate thread to ensure it doesn't block the UI thread.
                # Some Kivy audio providers might block the main loop while starting/playing.
                threading.Thread(target=self.alert_sound.play, daemon=True).start()
            self._last_alert_time = now

    def on_leave(self, *args):
        self.stop_audio()

# Register for use in .kv files
Factory.register('NoiseBarGraph', cls=NoiseBarGraph)
