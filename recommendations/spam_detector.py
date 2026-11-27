"""
Spam & Anomaly Detection using Isolation Forest for Research Commons.

Extracts per-account behavioral features:
- Event burst frequency (peak events per hour & average hourly burstiness)
- Post duplication ratio (repeated titles / boilerplate content)
- Repetitive commercial promotion links & promotional keywords
- Posting velocity concentration

Runs `sklearn.ensemble.IsolationForest` to flag suspicious accounts with
risk scores and human-readable explanation reasons for administrators.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import timedelta
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from recommendations.data_loader import ResearchCommonsData, load_data, parse_timestamp

URL_OR_DOMAIN_RE = re.compile(
    r"(https?://\S+|\b[\w-]+\.(?:com|org|net|io|biz|info)\b)",
    re.IGNORECASE,
)
REF_SUFFIX_RE = re.compile(r"\[ref\s*#\d+\]", re.IGNORECASE)
PROMO_KEYWORDS = (
    "guaranteed",
    "promo",
    "discount",
    "buy ",
    "fast-track",
    "fast track",
    "citation boost",
    "citations 10x",
    "h-index boost",
    "ghostwriter",
    "scopus",
    "dm for",
    "limited time",
    "100% guaranteed",
)


class SpamDetector:
    """Isolation Forest outlier detector for suspicious spam user accounts."""

    def __init__(
        self,
        data: ResearchCommonsData | None = None,
        contamination: float | str = "auto",
        random_state: int = 42,
    ) -> None:
        self.data = data if data is not None else load_data()
        self.contamination = contamination
        self.random_state = random_state

    @staticmethod
    def _normalize_post_signature(post: dict[str, Any]) -> str:
        title = str(post.get("title") or "").strip().lower()
        body = REF_SUFFIX_RE.sub("", str(post.get("content") or "")).strip().lower()
        return f"{title}::{body}"

    @staticmethod
    def _is_promotional_post(post: dict[str, Any]) -> bool:
        combined = f"{post.get('title', '')} {post.get('content', '')}".lower()
        tags = " ".join(str(t).lower() for t in (post.get("tags") or []))
        has_link = bool(URL_OR_DOMAIN_RE.search(combined))
        has_promo_kw = any(kw in combined or kw in tags for kw in PROMO_KEYWORDS)
        return has_link or has_promo_kw

    def _extract_user_features(self) -> tuple[list[dict[str, Any]], np.ndarray]:
        posts_by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)
        events_by_user: dict[int, list[dict[str, Any]]] = defaultdict(list)

        for post in self.data.posts:
            posts_by_user[int(post["user_id"])].append(post)
        for ev in self.data.activity_events:
            events_by_user[int(ev["user_id"])].append(ev)

        records: list[dict[str, Any]] = []
        feature_rows: list[list[float]] = []

        for user in self.data.users:
            uid = int(user["id"])
            u_posts = posts_by_user.get(uid, [])
            u_events = events_by_user.get(uid, [])

            # 1. Event burst frequency (events per hour & rolling 1-hour peak)
            hour_buckets: Counter[str] = Counter()
            event_times = []
            for ev in u_events:
                dt = parse_timestamp(ev.get("timestamp"))
                if dt is not None:
                    event_times.append(dt)
                    hour_buckets[dt.strftime("%Y-%m-%d %H")] += 1

            max_events_per_hour = max(hour_buckets.values(), default=0)
            mean_events_per_active_hour = (
                len(event_times) / len(hour_buckets) if hour_buckets else 0.0
            )

            # 2. Post duplication ratio
            total_posts = len(u_posts)
            if total_posts > 0:
                sigs = [self._normalize_post_signature(p) for p in u_posts]
                unique_sigs = len(set(sigs))
                post_duplication_ratio = 1.0 - (unique_sigs / total_posts)
            else:
                post_duplication_ratio = 0.0

            # 3. Repetitive commercial promotion links / promo content ratio
            promo_posts = sum(1 for p in u_posts if self._is_promotional_post(p))
            promo_link_ratio = (promo_posts / total_posts) if total_posts > 0 else 0.0

            # 4. Posting burst concentration (posts within active span)
            post_times = [
                dt for p in u_posts if (dt := parse_timestamp(p.get("created_at"))) is not None
            ]
            if len(post_times) >= 2:
                span_days = max((max(post_times) - min(post_times)).total_seconds() / 86400.0, 1.0)
                posts_per_day = total_posts / span_days
            else:
                posts_per_day = float(total_posts)

            # 5. Repeated identical search query ratio
            search_queries = [
                str(ev.get("query_text") or "").strip().lower()
                for ev in u_events
                if ev.get("event_type") == "search" and ev.get("query_text")
            ]
            if search_queries:
                most_common_q = Counter(search_queries).most_common(1)[0][1]
                query_repetition_ratio = most_common_q / len(search_queries)
            else:
                query_repetition_ratio = 0.0

            # 6. Burst within tight 72h window of latest activity
            if event_times:
                latest_ev = max(event_times)
                recent_ev_count = sum(1 for dt in event_times if dt >= latest_ev - timedelta(hours=72))
                recent_event_density = recent_ev_count / max(len(event_times), 1)
            else:
                recent_event_density = 0.0

            features = [
                float(max_events_per_hour),
                float(mean_events_per_active_hour),
                float(post_duplication_ratio),
                float(promo_link_ratio),
                float(posts_per_day),
                float(query_repetition_ratio),
                float(recent_event_density),
            ]
            feature_rows.append(features)
            records.append(
                {
                    "user": user,
                    "features": {
                        "total_posts": total_posts,
                        "total_events": len(u_events),
                        "max_events_per_hour": int(max_events_per_hour),
                        "mean_events_per_active_hour": round(mean_events_per_active_hour, 2),
                        "post_duplication_ratio": round(post_duplication_ratio, 4),
                        "promo_link_ratio": round(promo_link_ratio, 4),
                        "posts_per_day": round(posts_per_day, 2),
                        "query_repetition_ratio": round(query_repetition_ratio, 4),
                    },
                }
            )

        matrix = np.array(feature_rows, dtype=float) if feature_rows else np.empty((0, 7))
        return records, matrix

    @staticmethod
    def _explain_flags(feat: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if feat["max_events_per_hour"] >= 8 or feat["mean_events_per_active_hour"] >= 4.0:
            reasons.append(
                f"Abnormal event burst frequency (peak {feat['max_events_per_hour']} events/hr, "
                f"avg {feat['mean_events_per_active_hour']}/active hr)"
            )
        if feat["post_duplication_ratio"] >= 0.5:
            reasons.append(
                f"High post duplication ratio ({feat['post_duplication_ratio'] * 100:.0f}% repeated content)"
            )
        if feat["promo_link_ratio"] >= 0.3:
            reasons.append(
                f"Repetitive commercial promotional links/keywords ({feat['promo_link_ratio'] * 100:.0f}% of posts)"
            )
        if feat["posts_per_day"] >= 2.0:
            reasons.append(f"High posting velocity ({feat['posts_per_day']:.1f} posts/day)")
        if feat["query_repetition_ratio"] >= 0.6:
            reasons.append(
                f"Automated repetitive search queries ({feat['query_repetition_ratio'] * 100:.0f}% identical)"
            )
        if not reasons:
            reasons.append("Multivariate behavioral outlier detected by Isolation Forest")
        return reasons

    def detect_spam_accounts(self, include_all: bool = False) -> list[dict[str, Any]]:
        """
        Run Isolation Forest across all users and return flagged spam accounts
        sorted by descending risk score (or all accounts when `include_all=True`).
        """
        records, matrix = self._extract_user_features()
        if len(records) < 2:
            return []

        scaler = StandardScaler()
        scaled = scaler.fit_transform(matrix)

        model = IsolationForest(
            n_estimators=200,
            contamination=self.contamination,
            random_state=self.random_state,
        )
        preds = model.fit_predict(scaled)
        # decision_function: negative values indicate outliers
        decision_scores = model.decision_function(scaled)

        min_df = float(np.min(decision_scores))
        max_df = float(np.max(decision_scores))
        span = (max_df - min_df) or 1.0

        results: list[dict[str, Any]] = []
        for idx, rec in enumerate(records):
            user = rec["user"]
            feat = rec["features"]
            df_score = float(decision_scores[idx])
            is_outlier = int(preds[idx]) == -1

            # Require at least one strong behavioral spam indicator alongside IF outlier
            # prediction so benign template-based normal members are not falsely flagged.
            has_spam_signal = (
                feat["post_duplication_ratio"] >= 0.75
                or feat["promo_link_ratio"] >= 0.25
                or feat["max_events_per_hour"] >= 8
            )
            is_spam = bool(is_outlier and has_spam_signal)

            # Map decision score to 0..100 risk scale (higher = riskier)
            risk_score = round(((max_df - df_score) / span) * 100.0, 2)

            if not include_all and not is_spam:
                continue

            results.append(
                {
                    "user_id": int(user["id"]),
                    "name": user.get("name", ""),
                    "email": user.get("email", ""),
                    "department": user.get("department", ""),
                    "role": user.get("role", ""),
                    "is_spam": is_spam,
                    "isolation_forest_label": int(preds[idx]),
                    "anomaly_score": round(-df_score, 4),
                    "risk_score": risk_score,
                    "reasons": self._explain_flags(feat) if is_spam else [],
                    "features": feat,
                }
            )

        results.sort(key=lambda r: (r["is_spam"], r["risk_score"]), reverse=True)
        return results


_DEFAULT_SPAM_DETECTOR: SpamDetector | None = None


def detect_spam_accounts(include_all: bool = False) -> list[dict[str, Any]]:
    """Module-level helper delegating to a cached SpamDetector."""
    global _DEFAULT_SPAM_DETECTOR
    if _DEFAULT_SPAM_DETECTOR is None:
        _DEFAULT_SPAM_DETECTOR = SpamDetector()
    return _DEFAULT_SPAM_DETECTOR.detect_spam_accounts(include_all=include_all)
