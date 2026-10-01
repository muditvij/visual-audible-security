"""
Real-Time Audio Ingestion & Pipeline Orchestration Service.
Consumes continuous audio chunks from the host laptop microphone or ESP32 INMP441 I2S stream,
buffers frames in a circular array, runs asynchronous YAMNet inference, and synchronizes live
telemetry to connected Web Dashboard and physical ESP8266 sensory alert units.
"""

import time
import asyncio
import logging
import threading
import numpy as np
from scipy import signal
from typing import Dict, Any, Optional, Callable, List

from ml.audio.buffer_stream import AudioStreamBuffer
from ml.events.event_classifier import SoundEventClassifier
from backend.events.event_manager import event_manager
from backend.config.settings import settings

logger = logging.getLogger("EchoSense.AudioService")

class AudioService:
    def __init__(self):
        self.buffer = AudioStreamBuffer(max_buffer_seconds=5.0, sample_rate=settings.AUDIO_SAMPLE_RATE)
        self.classifier = SoundEventClassifier()
        self.is_running = False
        self._worker_thread: Optional[threading.Thread] = None
        
        # Audio source state: 'HOST_LAPTOP_MIC' or 'ESP32_INMP441'
        self.active_source: str = "HOST_LAPTOP_MIC"
        
        self.latest_telemetry: Dict[str, Any] = {
            "currentSound": "Monitoring",
            "rawLabel": "Silence",
            "confidence": 0.0,
            "status": "NORMAL",
            "activeSource": self.active_source,
            "device": self.active_source,
            "topPredictions": [],
            "validation": {
                "candidate": None,
                "confirmations": 0,
                "required": settings.TEMPORAL_REQUIRED_CONFIRMATIONS,
                "progressPct": 0
            },
            "rms": 0.0,
            "dbfs": -96.0,
            "snr": 0.0
        }
        self.telemetry_subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self.laptop_mic_stream = None
        self.is_laptop_mic_active = False
        self.laptop_mic_device = "Default Microphone"
        self._native_sample_rate: int = settings.AUDIO_SAMPLE_RATE

    def start(self):
        """Start the background audio processing worker thread."""
        if self.is_running:
            return
        self.is_running = True
        self._worker_thread = threading.Thread(target=self._processing_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Audio background inference worker started.")

    def stop(self):
        """Stop background worker and laptop mic."""
        self.stop_laptop_mic()
        self.is_running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        logger.info("Audio background worker stopped.")

    def set_audio_source(self, source: str) -> Dict[str, Any]:
        """
        Switch primary audio ingestion source between 'HOST_LAPTOP_MIC' and 'ESP32_INMP441'.
        When Laptop Mic is chosen, it is automatically engaged as main input.
        """
        clean_src = source.upper().strip()
        if "LAPTOP" in clean_src or "MIC" in clean_src:
            target = "HOST_LAPTOP_MIC"
        elif "ESP32" in clean_src or "INMP" in clean_src or "HARDWARE" in clean_src:
            target = "ESP32_INMP441"
        else:
            target = "HOST_LAPTOP_MIC"

        self.active_source = target
        logger.info(f"🔄 Active Audio Ingestion Source set to: {self.active_source}")

        if self.active_source == "HOST_LAPTOP_MIC":
            if not self.is_laptop_mic_active:
                self.start_laptop_mic()
        else:
            # Switching to ESP32: stop host laptop mic to prevent mixing
            if self.is_laptop_mic_active:
                self.stop_laptop_mic()
            self.buffer.clear()

        return {
            "activeSource": self.active_source,
            "isLaptopMicActive": self.is_laptop_mic_active,
            "device": self.active_source
        }

    def get_audio_source(self) -> Dict[str, Any]:
        return {
            "activeSource": self.active_source,
            "isLaptopMicActive": self.is_laptop_mic_active,
            "activeDevice": self.laptop_mic_device if self.active_source == "HOST_LAPTOP_MIC" else "ESP32_INMP441_I2S",
            "bufferSeconds": self.buffer.get_metrics().get("bufferedSeconds", 0.0),
            "sampleRate": self.buffer.sample_rate
        }

    def start_laptop_mic(self, device_index: Optional[int] = None) -> bool:
        """Start live audio ingestion directly from host laptop's internal microphone."""
        if self.is_laptop_mic_active:
            logger.info("Laptop microphone is already active.")
            return True

        try:
            import sounddevice as sd

            # Check supported sample rate
            target_sr = settings.AUDIO_SAMPLE_RATE  # 16000
            dev_info = sd.query_devices(device_index, 'input') if device_index is not None else sd.query_devices(kind='input')
            default_sr = int(dev_info.get('default_samplerate', target_sr))
            self.laptop_mic_device = dev_info.get('name', 'Default Microphone') if isinstance(dev_info, dict) else 'Default Microphone'

            # Try opening at 16000 Hz, or fallback to native sample rate with resampling
            use_resampling = False
            stream_sr = target_sr
            try:
                sd.check_input_settings(device=device_index, channels=1, dtype='float32', samplerate=target_sr)
            except Exception:
                stream_sr = default_sr
                use_resampling = True
                logger.info(f"Microphone driver requires native {stream_sr} Hz. Real-time resampler engaged.")

            self._native_sample_rate = stream_sr

            def _audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"Mic status: {status}")
                if self.active_source != "HOST_LAPTOP_MIC":
                    return

                samples = indata.flatten()
                if use_resampling and stream_sr != target_sr:
                    num_target = int(len(samples) * float(target_sr) / stream_sr)
                    samples = signal.resample(samples, num_target).astype(np.float32)

                self.buffer.write_samples(samples)

            logger.info(f"Opening host laptop microphone stream ({stream_sr} Hz -> 16000 Hz)...")
            self.laptop_mic_stream = sd.InputStream(
                samplerate=stream_sr,
                channels=1,
                dtype='float32',
                blocksize=int(stream_sr * 0.05),  # 50ms blocks
                device=device_index,
                callback=_audio_callback
            )
            self.laptop_mic_stream.start()
            self.is_laptop_mic_active = True
            self.active_source = "HOST_LAPTOP_MIC"
            logger.info(f"🎤 Host Laptop Microphone ACTIVE using: {self.laptop_mic_device}")
            return True
        except Exception as e:
            logger.error(f"Failed to start laptop microphone: {e}", exc_info=True)
            self.is_laptop_mic_active = False
            self.laptop_mic_stream = None
            return False

    def stop_laptop_mic(self) -> bool:
        """Stop host laptop microphone streaming."""
        if not self.is_laptop_mic_active or not self.laptop_mic_stream:
            self.is_laptop_mic_active = False
            return True

        try:
            logger.info("Stopping host laptop microphone...")
            self.laptop_mic_stream.stop()
            self.laptop_mic_stream.close()
            self.laptop_mic_stream = None
            self.is_laptop_mic_active = False
            logger.info("Host Laptop Microphone halted.")
            return True
        except Exception as e:
            logger.error(f"Error stopping laptop mic: {e}")
            self.is_laptop_mic_active = False
            self.laptop_mic_stream = None
            return False

    def ingest_pcm_chunk(self, pcm_bytes: bytes, sample_width: int = 2) -> int:
        """
        Called when ESP32 sends a packet of audio samples over WebSocket.
        Only ingests if active source is ESP32_INMP441, preventing cross-stream corruption.
        """
        if self.active_source != "ESP32_INMP441":
            # If laptop mic is currently active, ignore ESP32 audio packets
            return 0
        return self.buffer.write_pcm_bytes(pcm_bytes, sample_width)

    def subscribe_telemetry(self, callback: Callable[[Dict[str, Any]], None]):
        """Subscribe to live audio and inference telemetry."""
        self.telemetry_subscribers.append(callback)

    def _processing_loop(self):
        """Continuous sliding-window evaluation loop."""
        while self.is_running:
            try:
                if self.buffer.has_ready_window():
                    window = self.buffer.get_latest_window()
                    if window is not None:
                        result = self.classifier.process_window(window, source_device=self.active_source)
                        result["activeSource"] = self.active_source
                        result["device"] = self.active_source
                        self.latest_telemetry = result
                        
                        # Check if a validated safety event emerged
                        if result.get("validatedEvent"):
                            evt = result["validatedEvent"]
                            evt["device"] = self.active_source
                            logger.info(f"🚨 Dispatching validated safety event: {evt['displayLabel']} (Source: {self.active_source})")
                            event_manager.dispatch_validated_event(evt)
                            
                        # Broadcast live telemetry to connected clients
                        for sub in self.telemetry_subscribers:
                            try:
                                sub(result)
                            except Exception as e:
                                logger.error(f"Error in telemetry callback: {e}")
                else:
                    time.sleep(0.04)  # ~25Hz polling for accumulating audio
            except Exception as e:
                logger.error(f"Error in audio processing loop: {e}", exc_info=True)
                time.sleep(0.1)

    def replay_audio_file(self, filepath: str) -> Dict[str, Any]:
        """Run a stored WAV benchmark file sequentially through the pipeline."""
        logger.info(f"Starting replay verification for: {filepath}")
        results = self.classifier.process_wav_file(filepath)
        
        events_found = []
        for r in results:
            if r.get("validatedEvent"):
                r["validatedEvent"]["device"] = "FILE_REPLAY"
                event_manager.dispatch_validated_event(r["validatedEvent"])
                events_found.append(r["validatedEvent"])
                
        return {
            "file": filepath,
            "totalWindows": len(results),
            "eventsDetected": events_found,
            "finalState": self.latest_telemetry
        }

audio_service = AudioService()
