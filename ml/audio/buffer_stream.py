"""
Thread-Safe Streaming Circular Audio Buffer.
Accepts continuous chunks from ESP32 network sockets and yields sliding windows
for real-time pipeline inference without stalling or buffer blowouts.
"""

import threading
import numpy as np
from typing import Optional, Dict, Any

from ml.audio.preprocessor import TARGET_SAMPLE_RATE, WINDOW_SAMPLES, HOP_SAMPLES, AudioPreprocessor

class AudioStreamBuffer:
    def __init__(self, max_buffer_seconds: float = 5.0, sample_rate: int = TARGET_SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.max_samples = int(max_buffer_seconds * sample_rate)
        self.window_samples = WINDOW_SAMPLES
        self.hop_samples = HOP_SAMPLES
        self.preprocessor = AudioPreprocessor(target_sr=sample_rate)
        
        self._buffer = np.zeros(self.max_samples, dtype=np.float32)
        self._write_pos = 0
        self._total_samples_written = 0
        self._samples_since_last_window = 0
        self._lock = threading.Lock()
        
        self.overflow_count = 0
        self.underrun_count = 0

    def write_pcm_bytes(self, pcm_bytes: bytes, sample_width: int = 2) -> int:
        """Add raw PCM bytes into circular buffer. Returns count of samples added."""
        if not pcm_bytes:
            return 0
            
        float_samples = self.preprocessor.pcm_bytes_to_float(pcm_bytes, sample_width)
        return self.write_samples(float_samples)

    def write_samples(self, samples: np.ndarray) -> int:
        """Append float32 samples into circular array."""
        n_samples = len(samples)
        if n_samples == 0:
            return 0
            
        with self._lock:
            if n_samples > self.max_samples:
                # Buffer overflow: keep only latest max_samples
                samples = samples[-self.max_samples:]
                n_samples = len(samples)
                self.overflow_count += 1
                
            # Circular write
            end_pos = self._write_pos + n_samples
            if end_pos <= self.max_samples:
                self._buffer[self._write_pos:end_pos] = samples
            else:
                first_part = self.max_samples - self._write_pos
                second_part = n_samples - first_part
                self._buffer[self._write_pos:self.max_samples] = samples[:first_part]
                self._buffer[0:second_part] = samples[first_part:]
                
            self._write_pos = (self._write_pos + n_samples) % self.max_samples
            self._total_samples_written += n_samples
            self._samples_since_last_window += n_samples
            
        return n_samples

    def has_ready_window(self) -> bool:
        """Check if enough samples have accumulated to produce a new sliding window."""
        with self._lock:
            return (self._total_samples_written >= self.window_samples and 
                    self._samples_since_last_window >= self.hop_samples)

    def get_latest_window(self) -> Optional[np.ndarray]:
        """
        Extract the most recent 15,600 samples (0.975s) from the circular buffer.
        Advances hop counter.
        """
        with self._lock:
            if self._total_samples_written < self.window_samples:
                self.underrun_count += 1
                return None
                
            window = np.zeros(self.window_samples, dtype=np.float32)
            
            # Read backwards from _write_pos
            start_pos = (self._write_pos - self.window_samples) % self.max_samples
            
            if start_pos + self.window_samples <= self.max_samples:
                window[:] = self._buffer[start_pos:start_pos + self.window_samples]
            else:
                first_len = self.max_samples - start_pos
                second_len = self.window_samples - first_len
                window[:first_len] = self._buffer[start_pos:]
                window[first_len:] = self._buffer[:second_len]
                
            self._samples_since_last_window = 0
            
        return self.preprocessor.remove_dc_offset(window)

    def clear(self):
        """Reset buffer state."""
        with self._lock:
            self._buffer.fill(0)
            self._write_pos = 0
            self._total_samples_written = 0
            self._samples_since_last_window = 0

    def get_metrics(self) -> Dict[str, Any]:
        """Diagnostic state metrics."""
        with self._lock:
            return {
                "totalSamples": self._total_samples_written,
                "bufferedSeconds": round(min(self._total_samples_written, self.max_samples) / self.sample_rate, 2),
                "overflows": self.overflow_count,
                "underruns": self.underrun_count,
                "writePosition": self._write_pos
            }
