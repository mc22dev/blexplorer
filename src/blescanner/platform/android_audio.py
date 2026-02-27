import numpy as np
import threading
import time
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass
    AudioRecord = autoclass('android.media.AudioRecord')
    AudioSource = autoclass('android.media.MediaRecorder$AudioSource')
    AudioFormat = autoclass('android.media.AudioFormat')
    ByteBuffer = autoclass('java.nio.ByteBuffer')
    ByteOrder = autoclass('java.nio.ByteOrder')

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
            j_buffer.order(ByteOrder.nativeOrder())

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
            print(f"AndroidAudioRecorder: Error in read loop: {e}")
