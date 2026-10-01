"""
Temporal Sound Event Validator.
Prevents false alarms by enforcing multi-window persistence, RMS energy gating,
event cooldown, and priority conflict resolution across the full AudioSet taxonomy.
"""

import time
import logging
import numpy as np
from collections import deque
from typing import Dict, Any, Optional, List

from ml.validation.confidence_filter import ConfidenceFilter
from ml.yamnet.yamnet_mapping import map_yamnet_label_to_safety_event, SAFETY_CATEGORIES, PRIORITY_MAP

logger = logging.getLogger("EchoSense.Validator")

class TemporalValidator:
    def __init__(
        self,
        required_confirmations: int = 2,
        window_history_size: int = 3,
        confidence_filter: Optional[ConfidenceFilter] = None,
        cooldown_seconds: float = 20.0,
        min_rms: float = 0.010
    ):
        self.required_confirmations = required_confirmations
        self.window_history_size = window_history_size
        self.confidence_filter = confidence_filter or ConfidenceFilter()
        self.cooldown_seconds = cooldown_seconds
        self.min_rms = min_rms

        # Rolling history of window evaluations: deque of dicts
        self.window_history = deque(maxlen=window_history_size)
        
        # Cooldown tracker per category key
        self.last_event_triggered_time: Dict[str, float] = {}
        
        # Current active alert state
        self.active_alert: Optional[Dict[str, Any]] = None
        self.active_alert_start_time: float = 0.0
        
        # State indicators
        self.current_state = "NORMAL"  # NORMAL, VALIDATING, CONFIRMED, COOLDOWN
        self.current_candidate: Optional[str] = None
        self.current_confirmations: int = 0
        self.active_source_device: str = "HOST_LAPTOP_MIC"

    def set_source_device(self, device_name: str):
        """Set the active device identifier (e.g. 'HOST_LAPTOP_MIC' or 'ESP32_INMP441')."""
        self.active_source_device = device_name

    def process_window(
        self,
        top_predictions: List[Dict[str, Any]],
        rms: float,
        timestamp: Optional[float] = None,
        source_device: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single time window.
        Returns a dict summarizing:
        - state: NORMAL, VALIDATING, CONFIRMED, COOLDOWN
        - currentSound: Display label
        - rawLabel: Canonical AudioSet label
        - confidence: Current score
        - validation: { confirmations, required, progressPct }
        - validatedEvent: Event dict if a validated event just fired, else None
        """
        now = timestamp or time.time()
        active_dev = source_device or self.active_source_device
        
        # Check active alert timeout/duration
        if self.active_alert:
            elapsed = now - self.active_alert_start_time
            if elapsed > self.cooldown_seconds:
                logger.info(f"Active alert '{self.active_alert['displayLabel']}' completed cooldown period.")
                self.active_alert = None
                self.current_state = "NORMAL"

        # 1. RMS Energy Check
        if rms < self.min_rms:
            # Low energy is considered Ambient / Silence
            window_record = {
                "category": "NORMAL",
                "label": "Ambient / Silence",
                "rawLabel": "Silence",
                "score": 0.1,
                "tier": "NORMAL",
                "is_actionable": False,
                "priority": 4,
                "severity": "NORMAL",
                "timestamp": now,
                "config": SAFETY_CATEGORIES["NORMAL"]
            }
            self.window_history.append(window_record)
            self._update_candidate_state()
            return self._build_status_response(window_record, validated_event=None, top_predictions=top_predictions)

        # 2. Check top predictions against semantic category taxonomy
        best_candidate = None
        for pred in top_predictions:
            raw_label = pred.get("label", "")
            score = float(pred.get("score", 0.0))
            
            # Map raw label to safety category
            mapped = map_yamnet_label_to_safety_event(raw_label)
            tier, is_actionable = self.confidence_filter.evaluate(score, category=mapped["category"])
            
            candidate = {
                "category": mapped["category"],
                "label": mapped["displayLabel"],
                "rawLabel": raw_label,
                "score": score,
                "tier": tier,
                "is_actionable": is_actionable,
                "priority": mapped["priority"],
                "severity": mapped["severity"],
                "config": mapped,
                "timestamp": now
            }
            
            # Priority selection (Emergency / Critical > Warning > Info > Normal)
            if best_candidate is None:
                best_candidate = candidate
            elif candidate["priority"] < best_candidate["priority"] and candidate["is_actionable"]:
                best_candidate = candidate
            elif candidate["priority"] == best_candidate["priority"] and candidate["score"] > best_candidate["score"]:
                best_candidate = candidate

            # Stop early if a confirmed critical alert is identified
            if best_candidate and best_candidate["priority"] <= 1 and best_candidate["is_actionable"]:
                break

        if not best_candidate:
            top_raw = top_predictions[0] if top_predictions else {"label": "Ambient", "score": 0.5}
            raw_l = top_raw.get("label", "Ambient")
            mapped = map_yamnet_label_to_safety_event(raw_l)
            best_candidate = {
                "category": mapped["category"],
                "label": mapped["displayLabel"],
                "rawLabel": raw_l,
                "score": float(top_raw.get("score", 0.5)),
                "tier": "NORMAL",
                "is_actionable": False,
                "priority": mapped["priority"],
                "severity": mapped["severity"],
                "config": mapped,
                "timestamp": now
            }

        self.window_history.append(best_candidate)
        
        # 3. Multi-window temporal persistence validation
        validated_event = None
        cat = best_candidate["category"]
        
        # Determine if this category requires action (Alert or Warning)
        is_alert_category = best_candidate["severity"] in ("CRITICAL", "WARNING")
        
        if is_alert_category and best_candidate["is_actionable"]:
            # Check if this is an instantaneous explosive/shock event that can validate immediately
            is_instant_event = cat in ("EXPLOSION_GUNSHOT", "GLASS_BREAK") and best_candidate["score"] >= 0.50
            
            matches = [w for w in self.window_history if w.get("category") == cat and w.get("is_actionable")]
            confirmations = len(matches)
            if is_instant_event:
                confirmations = max(confirmations, self.required_confirmations)
                
            self.current_confirmations = confirmations
            self.current_candidate = best_candidate["label"]
            
            if confirmations >= self.required_confirmations:
                # Check cooldown
                last_time = self.last_event_triggered_time.get(cat, 0.0)
                if now - last_time < self.cooldown_seconds:
                    self.current_state = "COOLDOWN"
                    logger.debug(f"Event '{cat}' suppressed by cooldown ({round(now - last_time, 1)}s < {self.cooldown_seconds}s)")
                else:
                    # VALIDATED EVENT FIRED!
                    self.current_state = "CONFIRMED"
                    self.last_event_triggered_time[cat] = now
                    
                    scores_list = [m["score"] for m in matches]
                    mean_confidence = float(np.mean(scores_list)) if scores_list else best_candidate["score"]
                    duration_val = round(now - matches[0]["timestamp"], 2) if matches else 0.5
                    
                    cfg = best_candidate.get("config", {})
                    validated_event = {
                        "eventId": f"evt_{int(now * 1000)}",
                        "timestamp": now,
                        "source": "YAMNET",
                        "category": cat,
                        "rawLabel": best_candidate["rawLabel"],
                        "displayLabel": best_candidate["label"],
                        "confidence": round(mean_confidence, 2),
                        "severity": best_candidate["severity"],
                        "priority": best_candidate["priority"],
                        "validated": True,
                        "device": active_dev,
                        "notificationRequired": cfg.get("notificationRequired", False),
                        "rgbColor": cfg.get("rgbColor", [255, 0, 0]),
                        "rgbMode": cfg.get("rgbMode", "RED_PULSE"),
                        "lcdLine1": cfg.get("lcdLine1", "CRITICAL ALERT"),
                        "lcdLine2": cfg.get("lcdLine2", best_candidate["label"][:16]),
                        "buzzerPattern": cfg.get("buzzerPattern", "ALARM_BURST"),
                        "duration": duration_val
                    }
                    self.active_alert = validated_event
                    self.active_alert_start_time = now
                    logger.info(f"🚨 Validated safety event triggered: {validated_event['displayLabel']} (Confidence: {validated_event['confidence']}, Source: {active_dev})")
            else:
                self.current_state = "VALIDATING"
        else:
            self._update_candidate_state()

        return self._build_status_response(best_candidate, validated_event, top_predictions=top_predictions)

    def _update_candidate_state(self):
        """Reset validation counters if no actionable candidate in window."""
        actionable = [w for w in self.window_history if w.get("is_actionable")]
        if actionable:
            self.current_confirmations = len(actionable)
            self.current_candidate = actionable[-1].get("label", "Unknown")
            self.current_state = "VALIDATING"
        else:
            self.current_confirmations = 0
            self.current_candidate = None
            if not self.active_alert:
                self.current_state = "NORMAL"

    def _build_status_response(
        self,
        candidate: Dict[str, Any],
        validated_event: Optional[Dict[str, Any]],
        top_predictions: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Construct standard telemetry dictionary for live dashboard and devices."""
        progress_pct = int(min(1.0, (self.current_confirmations / max(1, self.required_confirmations))) * 100)
        
        return {
            "currentSound": candidate.get("label", "Monitoring"),
            "rawLabel": candidate.get("rawLabel", ""),
            "category": candidate.get("category", "NORMAL"),
            "severity": candidate.get("severity", "NORMAL"),
            "priority": candidate.get("priority", 4),
            "confidence": round(candidate.get("score", 0.0), 2),
            "tier": candidate.get("tier", "NORMAL"),
            "status": self.current_state,
            "device": self.active_source_device,
            "validation": {
                "candidate": self.current_candidate,
                "confirmations": self.current_confirmations,
                "required": self.required_confirmations,
                "progressPct": progress_pct
            },
            "activeAlert": self.active_alert,
            "validatedEvent": validated_event,
            "topPredictions": top_predictions or []
        }

    def reset(self):
        """Clear active alerts and reset state machines."""
        self.window_history.clear()
        self.active_alert = None
        self.current_state = "NORMAL"
        self.current_candidate = None
        self.current_confirmations = 0
