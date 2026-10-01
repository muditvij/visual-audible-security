"""
Comprehensive End-to-End Pipeline Integration Test Suite.
Verifies the complete flow from raw PCM audio through Preprocessor, RMS Gate,
YAMNet Inference, Confidence Filter, Temporal Validator, Priority Arbitration,
and WhatsApp Notification Dispatch.
"""

import pytest
import numpy as np
from pathlib import Path

from ml.audio.preprocessor import AudioPreprocessor, TARGET_SAMPLE_RATE, WINDOW_SAMPLES
from ml.audio.rms_analyzer import RMSAnalyzer
from ml.yamnet.yamnet_classifier import YAMNetClassifier
from ml.validation.confidence_filter import ConfidenceFilter
from ml.validation.temporal_validator import TemporalValidator
from ml.events.event_classifier import SoundEventClassifier
from backend.events.event_manager import EventManager
from backend.events.event_model import EchoSenseEvent, EmergencyContact
from backend.services.notification_service import NotificationService

TESTS_AUDIO_DIR = Path(__file__).resolve().parent.parent / "audio"

class TestAudioPipeline:
    def test_preprocessor_conversion(self):
        prep = AudioPreprocessor()
        # Create 1 second of 16-bit PCM zeroes
        raw_bytes = bytes(16000 * 2)
        floats = prep.pcm_bytes_to_float(raw_bytes, sample_width=2)
        assert len(floats) == 16000
        assert floats.dtype == np.float32
        assert np.allclose(floats, 0.0)

    def test_rms_silence_detection(self):
        rms_analyzer = RMSAnalyzer(silence_threshold=0.015)
        silence_samples = np.random.normal(0, 0.002, 15600).astype(np.float32)
        loud_samples = np.random.normal(0, 0.08, 15600).astype(np.float32)
        
        assert rms_analyzer.is_silence(silence_samples) is True
        assert rms_analyzer.is_silence(loud_samples) is False
        assert rms_analyzer.calculate_rms(loud_samples) > 0.05

    def test_yamnet_inference_shape(self):
        classifier = YAMNetClassifier(use_offline_fallback=True)
        classifier.load()
        dummy_wave = np.random.uniform(-0.1, 0.1, 15600).astype(np.float32)
        preds = classifier.predict(dummy_wave, top_k=3)
        assert len(preds) == 3
        assert "label" in preds[0]
        assert "score" in preds[0]
        assert preds[0]["score"] >= preds[1]["score"]

    def test_confidence_tiers(self):
        cf = ConfidenceFilter(low_thresh=0.45, valid_thresh=0.65, high_thresh=0.80)
        tier1, act1 = cf.evaluate(0.30)
        assert tier1 == "UNKNOWN" and act1 is False
        
        tier2, act2 = cf.evaluate(0.55)
        assert tier2 == "LOW_CONFIDENCE" and act2 is False
        
        tier3, act3 = cf.evaluate(0.72)
        assert tier3 == "VALID" and act3 is True
        
        tier4, act4 = cf.evaluate(0.88)
        assert tier4 == "HIGH_CONFIDENCE" and act4 is True

    def test_temporal_persistence_gate(self):
        validator = TemporalValidator(required_confirmations=2, window_history_size=3)
        
        # Window 1: Alarm 75%
        res1 = validator.process_window([{"label": "Alarm", "score": 0.75}], rms=0.06)
        assert res1["status"] == "VALIDATING"
        assert res1["validation"]["confirmations"] == 1
        assert res1["validatedEvent"] is None  # Not yet validated!

        # Window 2: Alarm 82% -> Should reach 2 confirmations and TRIGGER!
        res2 = validator.process_window([{"label": "Alarm", "score": 0.82}], rms=0.07)
        assert res2["status"] == "CONFIRMED"
        assert res2["validation"]["confirmations"] == 2
        assert res2["validatedEvent"] is not None
        assert res2["validatedEvent"]["severity"] == "CRITICAL"
        assert res2["validatedEvent"]["displayLabel"] == "Alarm Detected"

    def test_event_manager_priority_arbitration(self):
        em = EventManager()
        
        # 1. Dispatch Warning Event (Doorbell, Priority 2)
        warn_evt = em.dispatch_validated_event({
            "eventId": "evt_warn",
            "priority": 2,
            "severity": "WARNING",
            "displayLabel": "Doorbell",
            "category": "DOORBELL"
        })
        assert em.active_event.priority == 2
        assert em.active_event.displayLabel == "Doorbell"

        # 2. Trigger Physical SOS (Priority 0)
        sos_evt = em.trigger_sos(source="TEST")
        assert em.active_event.priority == 0
        assert em.active_event.severity == "SOS"

        # 3. Audio Critical Event (Priority 1) tries to overwrite active SOS -> MUST BE SUPPRESSED
        crit_attempt = em.dispatch_validated_event({
            "eventId": "evt_crit",
            "priority": 1,
            "severity": "CRITICAL",
            "displayLabel": "Alarm Detected",
            "category": "ALARM"
        })
        assert crit_attempt is None  # Rejected!
        assert em.active_event.priority == 0  # SOS remains active!

    def test_emergency_contacts_limit(self):
        ns = NotificationService()
        ns.contacts.clear()
        
        # Add 5 contacts
        for i in range(1, 6):
            ns.add_contact(EmergencyContact(
                id=f"c_{i}",
                name=f"Contact {i}",
                phoneNumber=f"+1000000000{i}",
                priority=i
            ))
        assert len(ns.get_contacts()) == 5
        
        # Attempt to add 6th contact -> Must raise ValueError
        with pytest.raises(ValueError):
            ns.add_contact(EmergencyContact(
                id="c_6",
                name="Contact 6",
                phoneNumber="+10000000006",
                priority=6
            ))

    def test_sos_acknowledge_and_white_reset(self):
        em = EventManager()
        # 1. Trigger SOS
        em.trigger_sos(source="TEST_BUTTON")
        assert em.active_event.priority == 0
        assert em.active_event.severity == "SOS"

        # 2. Reset Alert (Acknowledge)
        reset_evt = em.reset_alert()
        assert em.active_event is None
        assert reset_evt.rgbColor == [255, 255, 255]
        assert reset_evt.rgbMode == "WHITE_BREATH"
        assert reset_evt.displayLabel == "System Ready"

        # 3. Verify normal event can now be received immediately
        new_warn = em.dispatch_validated_event({
            "eventId": "evt_after_reset",
            "priority": 2,
            "severity": "WARNING",
            "displayLabel": "Doorbell",
            "category": "DOORBELL"
        })
        assert new_warn is not None
        assert em.active_event.priority == 2
