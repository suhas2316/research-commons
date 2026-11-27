"""
Trending Topics & Sudden Spike Detector using Sliding Window Z-Score Analysis.

Analyzes discussion post tags and search activity events across weekly sliding
windows, computing Z = (X - mu) / sigma against each topic's historical
baseline and raising alerts whenever Z > 2.5.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np

from recommendations.data_loader import ResearchCommonsData, load_data, parse_timestamp

DEFAULT_Z_THRESHOLD = 2.5
IGNORED_TAGS = {"trending", "promo", "fast publication", "citation boost"}


def _iso_week_key(dt: datetime) -> str:
    iso_year, iso_week, _ = dt.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _iso_week_bounds(iso_week_str: str) -> tuple[str, str]:
    year_str, week_part = iso_week_str.split("-W")
    monday = date.fromisocalendar(int(year_str), int(week_part), 1)
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), sunday.isoformat()


class TrendDetector:
    """Sliding-window Z-score trend and topic burst detector."""

    def __init__(
        self,
        data: ResearchCommonsData | None = None,
        z_threshold: float = DEFAULT_Z_THRESHOLD,
        min_spike_mentions: int = 5,
    ) -> None:
        self.data = data if data is not None else load_data()
        self.z_threshold = z_threshold
        self.min_spike_mentions = min_spike_mentions

        self._all_weeks: list[str] = []
        self._weekly_counts: dict[str, dict[str, int]] = {}
        self._daily_counts: dict[str, dict[date, int]] = {}
        self._latest_dt: datetime | None = None
        self._build_series()

    def _build_series(self) -> None:
        weekly: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        daily: dict[str, dict[date, int]] = defaultdict(lambda: defaultdict(int))
        timestamps: list[datetime] = []

        for post in self.data.posts:
            dt = parse_timestamp(post.get("created_at"))
            if dt is None:
                continue
            timestamps.append(dt)
            w_key = _iso_week_key(dt)
            d_key = dt.date()
            for raw_tag in post.get("tags") or []:
                topic = str(raw_tag).strip().lower()
                if topic and topic not in IGNORED_TAGS:
                    weekly[topic][w_key] += 1
                    daily[topic][d_key] += 1

        for ev in self.data.activity_events:
            if ev.get("event_type") != "search":
                continue
            query = str(ev.get("query_text") or "").strip().lower()
            if not query or "promo" in query:
                continue
            dt = parse_timestamp(ev.get("timestamp"))
            if dt is None:
                continue
            timestamps.append(dt)
            w_key = _iso_week_key(dt)
            d_key = dt.date()
            weekly[query][w_key] += 1
            daily[query][d_key] += 1

        self._weekly_counts = {t: dict(c) for t, c in weekly.items()}
        self._daily_counts = {t: dict(c) for t, c in daily.items()}

        if timestamps:
            min_dt = min(timestamps)
            max_dt = max(timestamps)
            self._latest_dt = max_dt
            weeks: list[str] = []
            seen: set[str] = set()
            cursor = min_dt.date() - timedelta(days=min_dt.weekday())
            end_date = max_dt.date()
            while cursor <= end_date:
                wk = _iso_week_key(datetime.combine(cursor, datetime.min.time(), tzinfo=timezone.utc))
                if wk not in seen:
                    seen.add(wk)
                    weeks.append(wk)
                cursor += timedelta(days=7)
            self._all_weeks = weeks
        else:
            self._all_weeks = []
            self._latest_dt = None

    def _compute_window_z(self, topic: str, target_week: str) -> tuple[int, float, float, float]:
        """Compute Z = (X - mu) / sigma for `topic` in `target_week` vs other weeks."""
        counts_by_week = self._weekly_counts.get(topic, {})
        x_val = counts_by_week.get(target_week, 0)
        baseline_weeks = [w for w in self._all_weeks if w != target_week]
        if not baseline_weeks:
            return x_val, 0.0, 1.0, 0.0

        baseline_series = np.array([counts_by_week.get(w, 0) for w in baseline_weeks], dtype=float)
        mu = float(np.mean(baseline_series))
        sigma = float(np.std(baseline_series, ddof=0))
        effective_sigma = max(sigma, 1.0)
        z_score = (x_val - mu) / effective_sigma
        return x_val, mu, sigma, z_score

    def detect_topic_spikes(
        self,
        z_threshold: float | None = None,
        recent_weeks: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Scan weekly sliding windows and return all topic spikes with Z > threshold.

        Args:
            z_threshold: Minimum Z-score required to trigger a spike alert (default 2.5).
            recent_weeks: Optional limit to inspect only the last N ISO weeks.
        """
        threshold = self.z_threshold if z_threshold is None else z_threshold
        if not self._all_weeks:
            return []

        weeks_to_scan = (
            self._all_weeks[-recent_weeks:] if recent_weeks and recent_weeks > 0 else self._all_weeks
        )

        alerts: list[dict[str, Any]] = []
        for topic in self._weekly_counts:
            for wk in weeks_to_scan:
                x_val, mu, sigma, z_score = self._compute_window_z(topic, wk)
                if x_val < self.min_spike_mentions:
                    continue
                if z_score > threshold:
                    week_start, week_end = _iso_week_bounds(wk)
                    severity = "critical" if z_score >= 5.0 else "high"
                    alerts.append(
                        {
                            "topic": topic,
                            "iso_week": wk,
                            "week_start": week_start,
                            "week_end": week_end,
                            "mentions": int(x_val),
                            "baseline_mean": round(mu, 2),
                            "baseline_std": round(sigma, 2),
                            "z_score": round(float(z_score), 2),
                            "alert_level": severity,
                            "alert": True,
                            "reason": (
                                f"Sudden surge in '{topic}' during {wk}: {x_val} mentions "
                                f"vs {mu:.2f} weekly avg (Z={z_score:.2f} > {threshold})"
                            ),
                        }
                    )

        alerts.sort(key=lambda a: (a["z_score"], a["mentions"]), reverse=True)
        return alerts

    def get_trending_topics(
        self,
        top_k: int = 10,
        window_days: int = 14,
    ) -> list[dict[str, Any]]:
        """
        Return top-K trending topics using sliding window comparison against
        historical baseline, incorporating recent velocity and peak Z-score alerts.
        """
        if top_k <= 0 or not self._all_weeks or self._latest_dt is None:
            return []

        anchor_date = self._latest_dt.date()
        recent_start = anchor_date - timedelta(days=max(window_days - 1, 0))
        prev_end = recent_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=max(window_days - 1, 0))

        # Index spike alerts by topic so recent/breaking surges are surfaced clearly
        spikes_by_topic: dict[str, dict[str, Any]] = {}
        for spike in self.detect_topic_spikes():
            t = spike["topic"]
            if t not in spikes_by_topic or spike["z_score"] > spikes_by_topic[t]["z_score"]:
                spikes_by_topic[t] = spike

        recent_weeks = self._all_weeks[-3:] if len(self._all_weeks) >= 3 else self._all_weeks
        ranked: list[dict[str, Any]] = []

        for topic, day_map in self._daily_counts.items():
            recent_mentions = sum(
                cnt for d, cnt in day_map.items() if recent_start <= d <= anchor_date
            )
            previous_mentions = sum(
                cnt for d, cnt in day_map.items() if prev_start <= d <= prev_end
            )
            total_mentions = sum(day_map.values())

            # Pick the highest Z-score across the recent sliding weeks (covers 7-21 day horizon)
            best_week = recent_weeks[-1]
            best_z = -999.0
            best_mu = 0.0
            best_sigma = 0.0
            best_week_mentions = 0
            for wk in recent_weeks:
                x_val, mu, sigma, z_val = self._compute_window_z(topic, wk)
                if z_val > best_z:
                    best_z = z_val
                    best_mu = mu
                    best_sigma = sigma
                    best_week = wk
                    best_week_mentions = x_val

            spike_info = spikes_by_topic.get(topic)
            is_spike = spike_info is not None and spike_info["iso_week"] in recent_weeks
            effective_z = spike_info["z_score"] if is_spike and spike_info else round(best_z, 2)

            growth_ratio = (
                (recent_mentions + 1.0) / (previous_mentions + 1.0)
            )
            trend_score = max(effective_z, 0.0) * 10.0 + recent_mentions * 0.5 + growth_ratio

            ranked.append(
                {
                    "topic": topic,
                    "recent_mentions": int(recent_mentions),
                    "previous_window_mentions": int(previous_mentions),
                    "total_mentions": int(total_mentions),
                    "peak_week": spike_info["iso_week"] if spike_info else best_week,
                    "peak_week_mentions": int(
                        spike_info["mentions"] if spike_info else best_week_mentions
                    ),
                    "baseline_mean": round(
                        spike_info["baseline_mean"] if spike_info else best_mu, 2
                    ),
                    "baseline_std": round(
                        spike_info["baseline_std"] if spike_info else best_sigma, 2
                    ),
                    "z_score": float(effective_z),
                    "is_spike": bool(best_z > self.z_threshold or is_spike),
                    "trend_status": "spike_alert" if (best_z > self.z_threshold or is_spike) else "steady",
                    "_rank_score": trend_score,
                }
            )

        ranked.sort(key=lambda r: (r["is_spike"], r["_rank_score"], r["recent_mentions"]), reverse=True)
        for item in ranked:
            item.pop("_rank_score", None)
        return ranked[:top_k]


_DEFAULT_TREND_DETECTOR: TrendDetector | None = None


def get_trending_topics(top_k: int = 10) -> list[dict[str, Any]]:
    """Module-level helper delegating to a cached TrendDetector."""
    global _DEFAULT_TREND_DETECTOR
    if _DEFAULT_TREND_DETECTOR is None:
        _DEFAULT_TREND_DETECTOR = TrendDetector()
    return _DEFAULT_TREND_DETECTOR.get_trending_topics(top_k=top_k)


def detect_topic_spikes(z_threshold: float = DEFAULT_Z_THRESHOLD) -> list[dict[str, Any]]:
    """Module-level helper returning Z-score topic spike alerts."""
    global _DEFAULT_TREND_DETECTOR
    if _DEFAULT_TREND_DETECTOR is None:
        _DEFAULT_TREND_DETECTOR = TrendDetector()
    return _DEFAULT_TREND_DETECTOR.detect_topic_spikes(z_threshold=z_threshold)
