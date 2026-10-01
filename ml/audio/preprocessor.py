"""
Audio Preprocessing Pipeline.
Transforms raw PCM byte streams and WAV buffers into calibrated 16 kHz mono float32 tensors.
Applies DC offset removal, optional resampling, and sliding window framing for YAMNet.
"""

import io
import wave
import numpy as np
from scipy import signal
from typing import List, Tuple, Generator

TARGET_SAMPLE_RATE = 16000
WINDOW_SAMPLES = 15600   # 0.975 seconds at 16 kHz (standard YAMNet receptive field)
HOP_SAMPLES = 8000       # 0.500 seconds hop (50% overlap)

class AudioPreprocessor:
    def __init__(self, target_sr: int = TARGET_SAMPLE_RATE):
        self.target_sr = target_sr
        # Design a 2nd order Butterworth high-pass filter at 60 Hz to strip DC bias and mechanical rumble
        b, a = signal.butter(2, 60.0 / (self.target_sr / 2.0), btype='highpass')
        self.hp_b = b
        self.hp_a = a

    def pcm_bytes_to_float(self, pcm_bytes: bytes, sample_width: int = 2) -> np.ndarray:
        """Convert raw signed integer PCM bytes to float32 in [-1.0, 1.0]."""
        if not pcm_bytes:
            return np.empty(0, dtype=np.float32)
            
        if sample_width == 2:  # 16-bit PCM
            data = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32)
            return data / 32768.0
        elif sample_width == 4:  # 32-bit PCM (e.g. raw 24/32-bit I2S)
            data = np.frombuffer(pcm_bytes, dtype=np.int32).astype(np.float32)
            return data / 2147483648.0
        elif sample_width == 1:  # 8-bit unsigned
            data = np.frombuffer(pcm_bytes, dtype=np.uint8).astype(np.float32)
            return (data - 128.0) / 128.0
        else:
            raise ValueError(f"Unsupported sample width: {sample_width}")

    def load_wav_file(self, filepath: str) -> Tuple[np.ndarray, int]:
        """Load standard WAV file and resample/downmix to 16 kHz mono float32."""
        with wave.open(filepath, 'rb') as wf:
            channels = wf.getnchannels()
            sample_width = wf.getsampwidth()
            framerate = wf.getframerate()
            n_frames = wf.getnframes()
            pcm_bytes = wf.readframes(n_frames)
            
        audio = self.pcm_bytes_to_float(pcm_bytes, sample_width)
        
        # De-interleave if multi-channel
        if channels > 1:
            audio = audio.reshape(-1, channels)
            audio = np.mean(audio, axis=1)  # Downmix to mono
            
        # Resample if not 16000 Hz
        if framerate != self.target_sr:
            num_samples = int(len(audio) * float(self.target_sr) / framerate)
            audio = signal.resample(audio, num_samples)
            
        audio = self.remove_dc_offset(audio)
        return audio, self.target_sr

    def remove_dc_offset(self, audio: np.ndarray) -> np.ndarray:
        """Apply zero-phase highpass filter or mean subtraction to remove sensor DC bias."""
        if len(audio) < 16:
            return audio
        try:
            return signal.filtfilt(self.hp_b, self.hp_a, audio).astype(np.float32)
        except Exception:
            # Fallback simple mean subtraction
            return (audio - np.mean(audio)).astype(np.float32)

    def extract_windows(self, audio: np.ndarray, window_size: int = WINDOW_SAMPLES, hop_size: int = HOP_SAMPLES) -> List[np.ndarray]:
        """Split 1D audio array into overlapping windows for temporal analysis."""
        if len(audio) < window_size:
            # Pad with zero reflection if shorter than one window
            padded = np.pad(audio, (0, window_size - len(audio)), mode='constant')
            return [padded]
            
        windows = []
        for start in range(0, len(audio) - window_size + 1, hop_size):
            windows.append(audio[start:start + window_size])
            
        return windows
