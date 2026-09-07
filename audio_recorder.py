"""
Audio recording utility for capturing microphone input.
Records to WAV format at 16kHz mono (optimal for STT).
"""

import os
import wave
import tempfile
import threading
from typing import Optional

import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False


class AudioRecorder:
    """Records audio from microphone to WAV file."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self._recording = False
        self._frames = []
        self._stream = None

    @staticmethod
    def is_available() -> bool:
        return HAS_AUDIO

    @staticmethod
    def get_input_devices() -> list:
        """Get list of available input devices."""
        if not HAS_AUDIO:
            return []
        devices = sd.query_devices()
        input_devices = []
        for i, dev in enumerate(devices):
            if dev['max_input_channels'] > 0:
                input_devices.append((i, dev['name']))
        return input_devices

    def start_recording(self):
        """Start recording audio in background."""
        if not HAS_AUDIO:
            raise RuntimeError("sounddevice not installed")
        self._recording = True
        self._frames = []

        def callback(indata, frames, time_info, status):
            if status:
                print(f"Audio status: {status}")
            if self._recording:
                self._frames.append(indata.copy())

        self._stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
            callback=callback,
        )
        self._stream.start()

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and save to temp WAV file.
        Returns path to saved file or None.
        """
        if not self._recording:
            return None

        self._recording = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._frames:
            return None

        # Concatenate frames and save
        audio_data = np.concatenate(self._frames, axis=0)

        # Convert float32 to int16 for WAV
        audio_int16 = (audio_data * 32767).astype(np.int16)

        tmp_path = tempfile.mktemp(suffix=".wav")
        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        self._frames = []
        return tmp_path

    def record_for_duration(self, duration_seconds: int) -> Optional[str]:
        """Record for a fixed duration and return file path."""
        if not HAS_AUDIO:
            raise RuntimeError("sounddevice not installed")

        audio_data = sd.rec(
            int(duration_seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype=np.float32,
        )
        sd.wait()

        audio_int16 = (audio_data * 32767).astype(np.int16)
        tmp_path = tempfile.mktemp(suffix=".wav")
        with wave.open(tmp_path, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_int16.tobytes())

        return tmp_path

    @property
    def is_recording(self) -> bool:
        return self._recording
