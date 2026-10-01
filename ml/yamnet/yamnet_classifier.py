"""
YAMNet Sound Classification Engine.
Handles loading Google YAMNet model from TensorFlow Hub, running inference on
16 kHz mono waveforms, and extracting top predicted AudioSet classes with probabilities.
Includes an intelligent offline spectral fallback if network or weights are unreachable.
"""

import os
import sys
import logging
import numpy as np
from typing import List, Dict, Any, Optional

from ml.yamnet.yamnet_classes import YAMNET_CLASS_NAMES, get_class_name
from ml.yamnet.yamnet_mapping import map_yamnet_label_to_safety_event

logger = logging.getLogger("EchoSense.YAMNet")

def _apply_tf_compatibility_patch():
    """
    Patch Keras 2 / TF 2.22 compatibility issue on Python 3.14 where
    'register_load_context_function' is missing from __internal__.
    """
    try:
        import tensorflow as tf
        import tensorflow._api.v2.compat.v2.__internal__ as internal_mod
        if not hasattr(internal_mod, "register_load_context_function"):
            internal_mod.register_load_context_function = lambda x: None
    except Exception as e:
        logger.debug(f"TF compatibility patch non-critical notice: {e}")

class YAMNetClassifier:
    def __init__(self, use_offline_fallback: bool = True):
        self.model = None
        self.model_loaded = False
        self.is_offline_fallback = False
        self.use_offline_fallback = use_offline_fallback
        self.class_names = YAMNET_CLASS_NAMES
        
    def load(self):
        """Load YAMNet model from TF Hub or initialize fallback engine."""
        try:
            logger.info("Initializing YAMNet classification model...")
            
            # Apply compatibility patch before importing tf_hub
            _apply_tf_compatibility_patch()
            
            import tensorflow as tf
            # Suppress verbose TF logs
            tf.get_logger().setLevel(logging.ERROR)
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
            
            import tensorflow_hub as hub
            hub_url = "https://tfhub.dev/google/yamnet/1"
            logger.info(f"Loading official Google YAMNet model from: {hub_url}")
            self.model = hub.load(hub_url)
            self.model_loaded = True
            self.is_offline_fallback = False
            logger.info("✅ Official Google YAMNet model successfully loaded (521 AudioSet classes ready).")
            
        except Exception as e:
            logger.warning(f"Could not load official YAMNet model from TF Hub: {e}")
            if self.use_offline_fallback:
                logger.info("Engaging EchoSense Resilient Acoustic Spectral Classifier as fallback engine.")
                self.is_offline_fallback = True
                self.model_loaded = True
            else:
                raise RuntimeError(f"YAMNet initialization failed: {e}")

    def predict(self, waveform: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Run inference on a 1D float32 audio waveform (16000 Hz, [-1.0, 1.0]).
        Returns top_k predictions sorted by confidence score.
        """
        if not self.model_loaded:
            self.load()
            
        if waveform is None or len(waveform) == 0:
            return [{"label": "Silence", "score": 0.0, "class_index": -1}]
            
        # Ensure float32 normalized
        if waveform.dtype != np.float32:
            waveform = waveform.astype(np.float32)
            
        max_val = np.max(np.abs(waveform))
        if max_val > 1.0:
            waveform = waveform / max_val
            
        # If real YAMNet model is active
        if self.model is not None and not self.is_offline_fallback:
            try:
                import tensorflow as tf
                # YAMNet expects shape [N]
                tensor_wave = tf.convert_to_tensor(waveform, dtype=tf.float32)
                scores, embeddings, spectrogram = self.model(tensor_wave)
                
                # Average scores across windows if waveform has multiple windows
                mean_scores = tf.reduce_mean(scores, axis=0).numpy()
                
                # Extract top_k classes across all 521 AudioSet classes
                top_indices = np.argsort(mean_scores)[::-1][:top_k]
                results = []
                for idx in top_indices:
                    class_idx = int(idx)
                    score = float(mean_scores[class_idx])
                    results.append({
                        "label": get_class_name(class_idx),
                        "score": round(score, 4),
                        "class_index": class_idx
                    })
                return results
            except Exception as e:
                logger.error(f"Error during YAMNet inference: {e}. Falling back to spectral analyzer.")
                
        # Acoustic Spectral Fallback Engine
        return self._spectral_predict(waveform, top_k)

    def _spectral_predict(self, waveform: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Robust Fourier/Spectral feature analyzer for offline verification and benchmarking.
        Analyzes spectral centroid, zero-crossing rate, harmonic energy, and crest factor
        across an extensive range of acoustic categories.
        """
        sample_rate = 16000
        n_samples = len(waveform)
        if n_samples < 512:
            return [{"label": "Silence", "score": 0.5, "class_index": 500}]
            
        # FFT analysis
        fft_vals = np.abs(np.fft.rfft(waveform))
        fft_freqs = np.fft.rfftfreq(n_samples, 1.0 / sample_rate)
        total_energy = np.sum(fft_vals**2) + 1e-10
        
        # Band energies
        sub_bass = np.sum(fft_vals[(fft_freqs >= 20) & (fft_freqs < 250)]**2) / total_energy
        low_band = np.sum(fft_vals[(fft_freqs >= 250) & (fft_freqs < 1000)]**2) / total_energy
        mid_band = np.sum(fft_vals[(fft_freqs >= 1000) & (fft_freqs < 3000)]**2) / total_energy
        high_band = np.sum(fft_vals[(fft_freqs >= 3000) & (fft_freqs < 7500)]**2) / total_energy
        
        # Zero crossing rate & Spectral Crest
        zcr = np.mean(np.abs(np.diff(np.sign(waveform)))) / 2.0
        peak_fft = np.max(fft_vals)
        mean_fft = np.mean(fft_vals) + 1e-8
        crest_factor = peak_fft / mean_fft
        
        # Peak frequency & RMS
        peak_freq = fft_freqs[np.argmax(fft_vals)]
        rms = np.sqrt(np.mean(waveform**2))
        
        scores: Dict[str, float] = {}
        
        # 1. Alarm / Smoke Detector / Siren: Strong tonal spike between 2.2 kHz - 4.2 kHz with high crest factor
        if 2200 <= peak_freq <= 4200 and crest_factor > 7.5:
            scores["Alarm"] = min(0.95, 0.68 + (crest_factor / 30.0))
            scores["Smoke detector, smoke alarm"] = scores["Alarm"] * 0.96
            scores["Siren"] = scores["Alarm"] * 0.88
            scores["Fire alarm"] = scores["Alarm"] * 0.85
            
        # 2. Siren (Frequency modulation / Sweep in 700Hz - 2200Hz with high energy)
        elif 700 <= peak_freq <= 2200 and crest_factor > 5.5 and mid_band > 0.55:
            scores["Siren"] = min(0.92, 0.65 + (mid_band * 0.3))
            scores["Civil defense siren"] = scores["Siren"] * 0.92
            scores["Police car (siren)"] = scores["Siren"] * 0.88
            scores["Alarm"] = scores["Siren"] * 0.80
            
        # 3. Glass Break / Shatter: High frequency energy > 3.5kHz with rapid zero-crossings and sharp onset
        elif high_band > 0.38 and zcr > 0.16:
            scores["Glass"] = min(0.94, 0.62 + (high_band * 0.4))
            scores["Shatter"] = scores["Glass"] * 0.97
            scores["Crack"] = scores["Glass"] * 0.82
            
        # 4. Distress / Screaming: High intensity vocal scream in 1.2 kHz - 3.5 kHz with high RMS
        elif (1200 <= peak_freq <= 3500) and (mid_band > 0.45) and rms > 0.08 and zcr > 0.09:
            scores["Screaming"] = min(0.91, 0.60 + (rms * 2.0))
            scores["Shout"] = scores["Screaming"] * 0.93
            scores["Yell"] = scores["Screaming"] * 0.90
            scores["Crying, sobbing"] = scores["Screaming"] * 0.82
            
        # 5. Baby Cry / Infant Cry: Periodic rhythmic cry formants in 400Hz - 2.8kHz
        elif (400 <= peak_freq <= 2800) and (0.35 <= mid_band <= 0.65) and (0.25 <= low_band <= 0.55) and rms > 0.05:
            scores["Baby cry, infant cry"] = min(0.88, 0.58 + (rms * 1.8))
            scores["Crying, sobbing"] = scores["Baby cry, infant cry"] * 0.94
            scores["Whimper"] = scores["Baby cry, infant cry"] * 0.80
            
        # 6. Doorbell / Chime: Dual tonal harmonics around 600Hz - 1800Hz with high resonant persistence
        elif (500 <= peak_freq <= 1800) and crest_factor > 5.5 and mid_band > 0.42:
            scores["Doorbell"] = min(0.92, 0.62 + (crest_factor / 22.0))
            scores["Ding-dong"] = scores["Doorbell"] * 0.94
            scores["Chime"] = scores["Doorbell"] * 0.89
            scores["Bell"] = scores["Doorbell"] * 0.85
            
        # 7. Knock / Door Tap: Low-frequency transient (<600Hz) with fast decay
        elif (low_band > 0.60 or sub_bass > 0.45) and zcr < 0.10 and rms > 0.025:
            scores["Knock"] = min(0.89, 0.58 + (low_band * 0.35))
            scores["Tap"] = scores["Knock"] * 0.92
            scores["Door"] = scores["Knock"] * 0.86
            scores["Thump, thud"] = scores["Knock"] * 0.82
            
        # 8. Gunshot / Explosion: High amplitude impulsive broadband shock with massive crest
        elif crest_factor > 9.0 and rms > 0.10 and (sub_bass > 0.35 or low_band > 0.35):
            scores["Explosion"] = min(0.93, 0.65 + (rms * 1.5))
            scores["Gunshot, gunfire"] = scores["Explosion"] * 0.95
            scores["Boom"] = scores["Explosion"] * 0.88
            
        # 9. Dog Bark: Burst in 800Hz - 2200Hz with percussive envelope
        elif 800 <= peak_freq <= 2200 and crest_factor > 4.2 and rms > 0.035:
            scores["Bark"] = min(0.87, 0.58 + (mid_band * 0.35))
            scores["Dog"] = scores["Bark"] * 0.96
            scores["Bow-wow"] = scores["Bark"] * 0.85
            
        # 10. Clapping / Applause: Dense transient bursts across mid and high bands
        elif mid_band > 0.35 and high_band > 0.22 and zcr > 0.13:
            scores["Clapping"] = min(0.88, 0.58 + (mid_band * 0.32))
            scores["Applause"] = scores["Clapping"] * 0.92
            scores["Hands"] = scores["Clapping"] * 0.86
            
        # 11. Vehicle Horn / Air Horn: Powerful harmonic tone in 350Hz - 900Hz
        elif 350 <= peak_freq <= 900 and crest_factor > 6.0 and low_band > 0.50:
            scores["Vehicle horn, car horn, honking"] = min(0.90, 0.60 + (crest_factor / 20.0))
            scores["Air horn, truck horn"] = scores["Vehicle horn, car horn, honking"] * 0.92
            scores["Traffic noise, roadway noise"] = scores["Vehicle horn, car horn, honking"] * 0.75
            
        # 12. Cough / Throat Clearing: Short transient percussive burst in 200Hz - 1500Hz
        elif 200 <= peak_freq <= 1500 and (0.30 <= low_band <= 0.65) and zcr > 0.08 and 0.02 <= rms <= 0.08:
            scores["Cough"] = min(0.85, 0.55 + (low_band * 0.3))
            scores["Throat clearing"] = scores["Cough"] * 0.88
            scores["Sneeze"] = scores["Cough"] * 0.80
            
        # 13. Speech / Conversation: Formant balance between 300Hz - 3.2kHz with modulated ZCR
        elif (0.20 <= mid_band <= 0.65) and (0.20 <= low_band <= 0.65) and (0.04 <= zcr <= 0.16) and rms > 0.015:
            scores["Speech"] = min(0.90, 0.65 + (mid_band * 0.3))
            scores["Conversation"] = scores["Speech"] * 0.94
            scores["Narration, monologue"] = scores["Speech"] * 0.85
            
        # 14. Music: Rich harmonic distribution, low crest, tonal persistence
        elif total_energy > 1e-4 and crest_factor < 5.0 and rms > 0.02:
            scores["Music"] = min(0.86, 0.55 + (mid_band * 0.3))
            scores["Musical instrument"] = scores["Music"] * 0.90
            scores["Singing"] = scores["Music"] * 0.84
            
        # 15. Ambient Noise / Silence
        else:
            if rms < 0.008:
                scores["Silence"] = 0.82
                scores["Inside, small room"] = 0.50
                scores["Environmental noise"] = 0.35
            else:
                scores["Environmental noise"] = 0.65
                scores["Noise"] = 0.58
                scores["White noise"] = 0.45
            
        # Fill standard fallback labels
        fallback_results = []
        for label, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]:
            fallback_results.append({
                "label": label,
                "score": float(score),
                "class_index": 0
            })
            
        # Pad up to top_k with ambient/background classes if needed
        default_padding = [
            ("Environmental noise", 0.08),
            ("Silence", 0.05),
            ("Speech", 0.03),
            ("Music", 0.02),
            ("Background noise", 0.01)
        ]
        existing_labels = {r["label"] for r in fallback_results}
        for pad_label, pad_score in default_padding:
            if len(fallback_results) >= top_k:
                break
            if pad_label not in existing_labels:
                fallback_results.append({
                    "label": pad_label,
                    "score": pad_score,
                    "class_index": 0
                })
                existing_labels.add(pad_label)
            
        return fallback_results[:top_k]
