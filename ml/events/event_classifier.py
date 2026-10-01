"""
Unified Sound Event Classification Pipeline.
Orchestrates audio preprocessing, RMS energy gating, YAMNet inference,
confidence filtering, and temporal validation into a unified pipeline.
"""

import time
import logging
import numpy as np
from typing import Dict, Any, List, Optional

from ml.audio.preprocessor import AudioPreprocessor
from ml.audio.rms_analyzer import RMSAnalyzer
from ml.yamnet.yamnet_classifier import YAMNetClassifier
from ml.validation.temporal_validator import TemporalValidator
from ml.validation.confidence_filter import ConfidenceFilter

logger = logging.getLogger("EchoSense.Pipeline")

class SoundEventClassifier:
    def __init__(
        self,
        classifier: Optional[YAMNetClassifier] = None,
        validator: Optional[TemporalValidator] = None,
        rms_analyzer: Optional[RMSAnalyzer] = None,
        preprocessor: Optional[AudioPreprocessor] = None
    ):
        self.preprocessor = preprocessor or AudioPreprocessor()
        self.rms_analyzer = rms_analyzer or RMSAnalyzer()
        self.classifier = classifier or YAMNetClassifier()
        self.validator = validator or TemporalValidator()

    def process_window(self, waveform: np.ndarray, timestamp: float = None, source_device: Optional[str] = None) -> Dict[str, Any]:
        """
        Process a single 0.975s window:
        1. Calculate RMS & SNR
        2. If silence/low-energy, bypass heavy ML
        3. Run YAMNet inference
        4. Pass through temporal persistence validator
        5. Return standardized result
        """
        ts = timestamp or time.time()
        
        # 1. RMS Energy
        rms = self.rms_analyzer.calculate_rms(waveform)
        dbfs = self.rms_analyzer.calculate_dbfs(rms)
        snr = self.rms_analyzer.calculate_snr(rms)
        
        # 2. Check if silence
        if self.rms_analyzer.is_silence(waveform):
            predictions = [{"label": "Silence", "score": 0.15, "class_index": 500}]
        else:
            # 3. YAMNet inference across full 521 classes
            predictions = self.classifier.predict(waveform, top_k=5)
            
        # 4. Temporal Validation
        validation_result = self.validator.process_window(predictions, rms=rms, timestamp=ts, source_device=source_device)
        
        # Attach acoustic signal metrics
        validation_result["rms"] = round(rms, 4)
        validation_result["dbfs"] = round(dbfs, 1)
        validation_result["snr"] = round(snr, 1)
        validation_result["topPredictions"] = predictions
        if source_device:
            validation_result["device"] = source_device
        
        return validation_result

    def process_pcm_bytes(self, pcm_bytes: bytes, sample_width: int = 2) -> Dict[str, Any]:
        """Convenience method to process raw PCM byte block."""
        float_wave = self.preprocessor.pcm_bytes_to_float(pcm_bytes, sample_width)
        return self.process_window(float_wave)

    def process_wav_file(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Process an entire WAV file frame-by-frame (used for Replay Mode and Automated Testing).
        """
        audio, sr = self.preprocessor.load_wav_file(filepath)
        windows = self.preprocessor.extract_windows(audio)
        
        results = []
        start_time = time.time()
        for idx, win in enumerate(windows):
            window_ts = start_time + (idx * 0.5)
            res = self.process_window(win, timestamp=window_ts)
            res["windowIndex"] = idx
            res["windowTimestampSeconds"] = round(idx * 0.5, 2)
            results.append(res)
            
        return results

    def reset(self):
        """Reset validation and acoustic tracking."""
        self.validator.reset()
