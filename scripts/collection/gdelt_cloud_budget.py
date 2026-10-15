"""Local safety budget for the GDELT Cloud Academic & Research plan.

The provider currently grants 5,000 QU/month.  This module deliberately keeps
an internal reserve below that entitlement and counts attempted HTTP calls
(including retries), so a failed request cannot silently exhaust the account.
It is a local guard, not an authoritative billing meter; the GDELT Cloud usage
page remains the source of truth.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class GDELTCloudBudgetExceeded(RuntimeError):
    """Raised before a request that would cross a local safety limit."""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _int_env(name: str, default: int, *, minimum: int = 0) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(value, minimum)


class GDELTCloudBudget:
    """Persist a conservative request budget under ``data/gdelt_cloud``."""

    def __init__(self, state_path: Path):
        self.state_path = state_path
        self.monthly_cap = _int_env("GDELT_CLOUD_MONTHLY_SAFETY_CAP", 4500)
        self.daily_cap = _int_env("GDELT_CLOUD_DAILY_SAFETY_CAP", 100)
        self.min_interval_sec = float(os.getenv("GDELT_CLOUD_MIN_INTERVAL_SEC", "2"))

    def _load(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        try:
            value = json.loads(self.state_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            # A corrupt local meter must fail closed rather than spend blindly.
            raise GDELTCloudBudgetExceeded(
                f"GDELT Cloud local budget state is unreadable: {self.state_path}"
            )

    def _save(self, state: dict[str, Any]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.state_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(self.state_path)

    def reserve(self, units: int = 1, *, reason: str = "request") -> dict[str, Any]:
        """Reserve request units before an HTTP call and return meter metadata."""
        if units < 1:
            raise ValueError("units must be >= 1")
        now = _utc_now()
        month = now.strftime("%Y-%m")
        day = now.strftime("%Y-%m-%d")
        state = self._load()
        if state.get("month") != month:
            state = {"month": month, "month_units": 0, "day": day, "day_units": 0}
        elif state.get("day") != day:
            state["day"] = day
            state["day_units"] = 0

        month_units = int(state.get("month_units", 0))
        day_units = int(state.get("day_units", 0))
        if month_units + units > self.monthly_cap:
            raise GDELTCloudBudgetExceeded(
                f"monthly local safety cap reached ({month_units}/{self.monthly_cap} QU)"
            )
        if day_units + units > self.daily_cap:
            raise GDELTCloudBudgetExceeded(
                f"daily local safety cap reached ({day_units}/{self.daily_cap} QU)"
            )

        state["month_units"] = month_units + units
        state["day_units"] = day_units + units
        state["last_reserved_at"] = now.isoformat()
        state["last_reason"] = reason
        self._save(state)
        return {
            "month": month,
            "month_units": state["month_units"],
            "month_cap": self.monthly_cap,
            "day": day,
            "day_units": state["day_units"],
            "day_cap": self.daily_cap,
        }

    def wait_for_interval(self) -> None:
        """Throttle calls without sleeping when the configured interval is zero."""
        if self.min_interval_sec <= 0:
            return
        state = self._load()
        last = state.get("last_call_at")
        if last:
            try:
                elapsed = (_utc_now() - datetime.fromisoformat(last)).total_seconds()
                if elapsed < self.min_interval_sec:
                    time.sleep(self.min_interval_sec - elapsed)
            except (TypeError, ValueError):
                pass
        state["last_call_at"] = _utc_now().isoformat()
        self._save(state)

    def snapshot(self) -> dict[str, Any]:
        state = self._load()
        return {
            "month": state.get("month"),
            "month_units": int(state.get("month_units", 0)),
            "month_cap": self.monthly_cap,
            "day": state.get("day"),
            "day_units": int(state.get("day_units", 0)),
            "day_cap": self.daily_cap,
            "state_path": str(self.state_path),
        }
