# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Validation monitoring and metrics utilities.

Provides lightweight tracking for validation successes and failures,
including persistence to disk so operations teams can monitor trends
and regression risk.
"""

import json
import os
import time
from typing import Dict, List, Optional

from src.services.logging_service import logging_service

logger = logging_service.get_logger(__name__)


class ValidationMonitor:
    """Track validation successes and failures with persistence."""

    def __init__(self, metrics_file: str) -> None:
        """
        Initialize the monitor.

        Args:
            metrics_file: Destination file for persisted metrics.
        """
        self.metrics_file = metrics_file
        self._ensure_directory()
        self.metrics = {
            "total_events": 0,
            "successes": 0,
            "failures": 0,
            "successes_by_endpoint": {},
            "failures_by_endpoint": {},
            "recent_failures": [],
            "last_updated": None,
        }
        self._load_from_disk()

    def _ensure_directory(self) -> None:
        """Create the metrics directory if missing."""
        directory = os.path.dirname(self.metrics_file)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def _load_from_disk(self) -> None:
        """Load existing metrics if available."""
        if not os.path.exists(self.metrics_file):
            return

        try:
            with open(self.metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.metrics.update(data)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "ValidationMonitor failed to load metrics",
                extra={
                    "event": "validation.monitor.load",
                    "resource_id": self.metrics_file,
                    "status": "failure",
                },
                exc_info=exc,
            )

    def _persist(self) -> None:
        """Persist metrics to disk."""
        self.metrics["last_updated"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
        )
        try:
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "ValidationMonitor failed to persist metrics",
                extra={
                    "event": "validation.monitor.persist",
                    "resource_id": self.metrics_file,
                    "status": "failure",
                },
                exc_info=exc,
            )

    def record_event(
        self,
        endpoint: str,
        success: bool,
        errors: Optional[List[str]] = None,
        client: Optional[str] = None,
    ) -> None:
        """
        Record a validation result.

        Args:
            endpoint: API path being validated.
            success: Whether validation passed.
            errors: Optional list of error messages.
            client: Optional client identifier (e.g., IP or user agent).
        """
        self.metrics["total_events"] += 1

        if success:
            self.metrics["successes"] += 1
            self.metrics["successes_by_endpoint"][endpoint] = (
                self.metrics["successes_by_endpoint"].get(endpoint, 0) + 1
            )
        else:
            self.metrics["failures"] += 1
            self.metrics["failures_by_endpoint"][endpoint] = (
                self.metrics["failures_by_endpoint"].get(endpoint, 0) + 1
            )
            failure_entry = {
                "endpoint": endpoint,
                "errors": errors or [],
                "client": client,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            # Keep only the 20 most recent failures
            recent = self.metrics.get("recent_failures", [])
            recent.append(failure_entry)
            self.metrics["recent_failures"] = recent[-20:]

        self._persist()

    def snapshot(self) -> Dict[str, object]:
        """
        Return a snapshot of metrics augmented with failure rate.

        Returns:
            Dict[str, object]: Current metrics with calculated failure rate.
        """
        total = max(self.metrics.get("total_events", 0), 1)
        failure_rate = self.metrics.get("failures", 0) / total

        snapshot = dict(self.metrics)
        snapshot["failure_rate"] = round(failure_rate, 4)
        return snapshot
