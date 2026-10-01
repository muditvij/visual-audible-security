"""
Confidence Level Filter.
Categorizes prediction confidence scores into defined operational tiers
and applies calibrated classification gates for 521-class AudioSet taxonomy.
"""

from typing import Tuple, Optional

class ConfidenceFilter:
    def __init__(
        self,
        low_thresh: float = 0.15,
        valid_thresh: float = 0.28,
        high_thresh: float = 0.55
    ):
        self.low_thresh = low_thresh
        self.valid_thresh = valid_thresh
        self.high_thresh = high_thresh

    def evaluate(self, score: float, category: Optional[str] = None) -> Tuple[str, bool]:
        """
        Classifies confidence into:
        - UNKNOWN (< low_thresh): Rejected
        - LOW_CONFIDENCE (low_thresh <= score < valid_thresh): Flagged for observation, not actionable
        - VALID (valid_thresh <= score < high_thresh): Eligible for temporal confirmation
        - HIGH_CONFIDENCE (score >= high_thresh): Strongly confirmed

        Returns (tier_label, is_actionable)
        """
        # Lower threshold for high-criticality life-safety alarms
        effective_valid = self.valid_thresh
        if category in ("SMOKE_FIRE_ALARM", "ALARM", "GLASS_BREAK", "DISTRESS"):
            effective_valid = max(0.22, self.valid_thresh * 0.85)

        if score < self.low_thresh:
            return "UNKNOWN", False
        elif score < effective_valid:
            return "LOW_CONFIDENCE", False
        elif score < self.high_thresh:
            return "VALID", True
        else:
            return "HIGH_CONFIDENCE", True

    def update_thresholds(self, low: float = None, valid: float = None, high: float = None):
        """Allow runtime threshold tuning."""
        if low is not None:
            self.low_thresh = low
        if valid is not None:
            self.valid_thresh = valid
        if high is not None:
            self.high_thresh = high
