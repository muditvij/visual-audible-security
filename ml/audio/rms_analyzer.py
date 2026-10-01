"""
RMS & Acoustic Signal Quality Analyzer.
Provides energy gating, dBFS calculation, noise floor tracking, and silence filtering
to discard low-energy ambient noise windows prior to YAMNet classification.
"""

import numpy as np

class RMSAnalyzer:
    def __init__(self, silence_threshold: float = 0.015, noise_adaptation_rate: float = 0.05):
        self.silence_threshold = silence_threshold
        self.noise_adaptation_rate = noise_adaptation_rate
        self.noise_floor_rms = 0.005  # Initial baseline
        
    def calculate_rms(self, samples: np.ndarray) -> float:
        """Calculate Root Mean Square energy of 1D float32 array in [-1.0, 1.0]."""
        if samples is None or len(samples) == 0:
            return 0.0
        return float(np.sqrt(np.mean(samples.astype(np.float32)**2)))
        
    def calculate_dbfs(self, rms: float) -> float:
        """Convert linear RMS to Decibels Full Scale (dBFS)."""
        if rms <= 1e-6:
            return -96.0  # Theoretical dynamic range limit for 16-bit PCM
        return float(20.0 * np.log10(rms))
        
    def update_noise_floor(self, rms: float) -> float:
        """Smoothly track ambient acoustic background noise floor."""
        if rms < self.silence_threshold * 1.5:
            self.noise_floor_rms = (1.0 - self.noise_adaptation_rate) * self.noise_floor_rms + (self.noise_adaptation_rate * rms)
        return self.noise_floor_rms

    def calculate_snr(self, rms: float) -> float:
        """Calculate Signal-to-Noise Ratio (dB) above ambient floor."""
        if self.noise_floor_rms <= 1e-6:
            return 30.0
        return float(20.0 * np.log10(max(rms, 1e-6) / self.noise_floor_rms))

    def is_silence(self, samples: np.ndarray, threshold: float = None) -> bool:
        """Return True if window energy is below the silence threshold."""
        thresh = threshold if threshold is not None else self.silence_threshold
        rms = self.calculate_rms(samples)
        self.update_noise_floor(rms)
        return rms < thresh
