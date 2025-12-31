"""
Metrics Collector for Feature Flags
Tracks flag evaluations and cutover progress
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict

from prometheus_client import Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Collects and exposes metrics for feature flags"""

    def __init__(self):
        # Counters
        self.flag_evaluations = Counter(
            'feature_flag_evaluations_total',
            'Total feature flag evaluations',
            ['flag_name', 'result']
        )

        self.phase_transitions = Counter(
            'cutover_phase_transitions_total',
            'Phase transition count',
            ['from_phase', 'to_phase']
        )

        # Gauges
        self.flag_percentage = Gauge(
            'feature_flag_percentage',
            'Current traffic percentage for flag',
            ['flag_name']
        )

        self.current_phase = Gauge(
            'cutover_current_phase',
            'Current cutover phase (encoded)',
            []
        )

        self.flags_enabled = Gauge(
            'feature_flags_enabled_total',
            'Number of enabled feature flags',
            []
        )

        # Histograms
        self.evaluation_latency = Histogram(
            'feature_flag_evaluation_seconds',
            'Time to evaluate a feature flag',
            ['flag_name'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1]
        )

        # Internal tracking
        self._evaluation_counts: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {"microservice": 0, "django": 0}
        )
        self._phase_encoding = {
            "shadow": 0,
            "canary": 1,
            "early_adopter": 2,
            "half": 3,
            "majority": 4,
            "final_validation": 5,
            "complete": 6,
            "rollback": -1,
        }

    def record_evaluation(
        self,
        flag_name: str,
        use_microservice: bool,
        evaluation_time: float
    ):
        """Record a flag evaluation"""
        result = "microservice" if use_microservice else "django"
        self.flag_evaluations.labels(flag_name=flag_name, result=result).inc()
        self.evaluation_latency.labels(flag_name=flag_name).observe(evaluation_time)
        self._evaluation_counts[flag_name][result] += 1

    def update_flag_percentage(self, flag_name: str, percentage: int):
        """Update the percentage gauge for a flag"""
        self.flag_percentage.labels(flag_name=flag_name).set(percentage)

    def update_current_phase(self, phase: str):
        """Update the current phase gauge"""
        phase_value = self._phase_encoding.get(phase, -2)
        self.current_phase.set(phase_value)

    def record_phase_transition(self, from_phase: str, to_phase: str):
        """Record a phase transition"""
        self.phase_transitions.labels(
            from_phase=from_phase,
            to_phase=to_phase
        ).inc()

    def update_enabled_count(self, count: int):
        """Update the count of enabled flags"""
        self.flags_enabled.set(count)

    def get_evaluation_stats(self) -> Dict[str, Any]:
        """Get evaluation statistics"""
        stats = {}
        for flag_name, counts in self._evaluation_counts.items():
            total = counts["microservice"] + counts["django"]
            if total > 0:
                ms_pct = (counts["microservice"] / total) * 100
                stats[flag_name] = {
                    "total_evaluations": total,
                    "microservice_count": counts["microservice"],
                    "django_count": counts["django"],
                    "microservice_percentage": round(ms_pct, 2),
                    "django_percentage": round(100 - ms_pct, 2),
                }
        return stats

    def get_prometheus_metrics(self) -> bytes:
        """Generate Prometheus metrics output"""
        return generate_latest()
