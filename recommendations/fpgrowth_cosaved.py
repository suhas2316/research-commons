"""
Co-Saved Paper Association Mining using FP-Growth for Research Commons.

Implements frequent pattern mining via `mlxtend.frequent_patterns.fpgrowth`
and `association_rules` over user library baskets to power:
"Members who saved this paper also saved..."
"""

from __future__ import annotations

import inspect
from collections import Counter
from typing import Any

import pandas as pd
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder

from recommendations.data_loader import ResearchCommonsData, load_data


class FPGrowthCosavedRecommender:
    """FP-Growth association rule miner over user library co-saves."""

    def __init__(
        self,
        data: ResearchCommonsData | None = None,
        min_support: float = 0.04,
        min_confidence: float = 0.30,
    ) -> None:
        self.data = data if data is not None else load_data()
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.baskets: list[list[str]] = []
        self.frequent_itemsets: pd.DataFrame = pd.DataFrame()
        self.rules: pd.DataFrame = pd.DataFrame()
        self._cooccurrence: dict[str, Counter[str]] = {}
        self._fit()

    def _build_baskets(self) -> list[list[str]]:
        user_papers: dict[int, set[str]] = {}
        for entry in self.data.library:
            uid = int(entry["user_id"])
            pid = str(entry["paper_id"])
            user_papers.setdefault(uid, set()).add(pid)

        baskets = [sorted(pids) for pids in user_papers.values() if pids]
        self._cooccurrence = {}
        for basket in baskets:
            for pid in basket:
                counter = self._cooccurrence.setdefault(pid, Counter())
                for other in basket:
                    if other != pid:
                        counter[other] += 1
        return baskets

    @staticmethod
    def _compute_association_rules(
        frequent_itemsets: pd.DataFrame,
        num_itemsets: int,
        min_confidence: float,
    ) -> pd.DataFrame:
        sig = inspect.signature(association_rules)
        kwargs: dict[str, Any] = {
            "metric": "confidence",
            "min_threshold": min_confidence,
        }
        if "num_itemsets" in sig.parameters:
            kwargs["num_itemsets"] = num_itemsets
        return association_rules(frequent_itemsets, **kwargs)

    def _fit(self) -> None:
        self.baskets = self._build_baskets()
        if not self.baskets:
            self.frequent_itemsets = pd.DataFrame()
            self.rules = pd.DataFrame()
            return

        te = TransactionEncoder()
        encoded = te.fit(self.baskets).transform(self.baskets)
        df_encoded = pd.DataFrame(encoded, columns=te.columns_)

        # Ensure support threshold requires at least 2 co-occurrences
        effective_support = max(self.min_support, 2.0 / len(self.baskets))
        if effective_support >= 1.0:
            effective_support = 1.0 / max(len(self.baskets), 1)

        self.frequent_itemsets = fpgrowth(
            df_encoded,
            min_support=effective_support,
            use_colnames=True,
        )
        if self.frequent_itemsets.empty:
            self.rules = pd.DataFrame()
            return

        rules_df = self._compute_association_rules(
            self.frequent_itemsets,
            num_itemsets=len(self.baskets),
            min_confidence=self.min_confidence,
        )
        if not rules_df.empty:
            rules_df = rules_df.sort_values(
                by=["confidence", "lift", "support"], ascending=[False, False, False]
            ).reset_index(drop=True)
        self.rules = rules_df

    def get_frequent_itemsets(self, min_length: int = 1) -> list[dict[str, Any]]:
        """Return mined frequent itemsets filtered by minimum itemset length."""
        if self.frequent_itemsets.empty:
            return []
        results: list[dict[str, Any]] = []
        for _, row in self.frequent_itemsets.iterrows():
            items = sorted(str(x) for x in row["itemsets"])
            if len(items) >= min_length:
                results.append(
                    {
                        "itemsets": items,
                        "length": len(items),
                        "support": round(float(row["support"]), 4),
                    }
                )
        results.sort(key=lambda r: (r["length"], r["support"]), reverse=True)
        return results

    def get_association_rules(self, top_k: int = 20) -> list[dict[str, Any]]:
        """Return top-K association rules sorted by confidence and lift."""
        if self.rules.empty:
            return []
        output: list[dict[str, Any]] = []
        for _, row in self.rules.head(top_k).iterrows():
            output.append(
                {
                    "antecedents": sorted(str(x) for x in row["antecedents"]),
                    "consequents": sorted(str(x) for x in row["consequents"]),
                    "support": round(float(row["support"]), 4),
                    "confidence": round(float(row["confidence"]), 4),
                    "lift": round(float(row["lift"]), 4),
                }
            )
        return output

    def get_cosaved_recommendations(
        self, paper_id: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Return top-K papers commonly co-saved alongside `paper_id`.

        Uses mined FP-Growth association rules first, with direct basket
        co-occurrence fallback when a paper sits below the support threshold.
        """
        pid = str(paper_id)
        if top_k <= 0:
            return []

        best_by_consequent: dict[str, dict[str, Any]] = {}
        co_counts = self._cooccurrence.get(pid, Counter())

        if not self.rules.empty:
            for _, row in self.rules.iterrows():
                antecedents = {str(x) for x in row["antecedents"]}
                if pid not in antecedents:
                    continue
                for cons_id in row["consequents"]:
                    cid = str(cons_id)
                    if cid == pid:
                        continue
                    candidate = {
                        "paper_id": cid,
                        "support": float(row["support"]),
                        "confidence": float(row["confidence"]),
                        "lift": float(row["lift"]),
                        "antecedents": sorted(antecedents),
                        "source": "fpgrowth_rule",
                    }
                    existing = best_by_consequent.get(cid)
                    if existing is None or (
                        candidate["confidence"],
                        candidate["lift"],
                        candidate["support"],
                    ) > (
                        existing["confidence"],
                        existing["lift"],
                        existing["support"],
                    ):
                        best_by_consequent[cid] = candidate

        ranked = sorted(
            best_by_consequent.values(),
            key=lambda r: (r["confidence"], r["lift"], r["support"]),
            reverse=True,
        )

        # Backfill with raw co-occurrence counts if rules yield fewer than top_k
        if len(ranked) < top_k and co_counts:
            seen = {r["paper_id"] for r in ranked}
            total_baskets = max(len(self.baskets), 1)
            pid_count = sum(1 for b in self.baskets if pid in b) or 1
            for other_id, count in co_counts.most_common():
                if other_id in seen:
                    continue
                seen.add(other_id)
                ranked.append(
                    {
                        "paper_id": other_id,
                        "support": count / total_baskets,
                        "confidence": count / pid_count,
                        "lift": 1.0,
                        "antecedents": [pid],
                        "source": "cooccurrence_fallback",
                    }
                )
                if len(ranked) >= top_k:
                    break

        results: list[dict[str, Any]] = []
        for item in ranked[:top_k]:
            cid = item["paper_id"]
            paper = self.data.papers_by_id.get(cid, {})
            co_save_count = int(co_counts.get(cid, 0))
            conf_pct = round(item["confidence"] * 100, 1)
            results.append(
                {
                    "paper_id": cid,
                    "title": paper.get("title", ""),
                    "authors": paper.get("authors", []),
                    "publication_year": paper.get("publication_year"),
                    "citation_count": int(paper.get("citation_count") or 0),
                    "concepts": paper.get("concepts", []),
                    "support": round(float(item["support"]), 4),
                    "confidence": round(float(item["confidence"]), 4),
                    "lift": round(float(item["lift"]), 4),
                    "co_save_count": co_save_count,
                    "rule_source": item["source"],
                    "reason": (
                        f"{conf_pct}% of members who saved this paper also saved "
                        f"'{paper.get('title', cid)}' (lift {item['lift']:.2f})"
                    ),
                }
            )
        return results


_DEFAULT_FPGROWTH: FPGrowthCosavedRecommender | None = None


def get_cosaved_recommendations(paper_id: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Module-level helper delegating to a cached FPGrowthCosavedRecommender."""
    global _DEFAULT_FPGROWTH
    if _DEFAULT_FPGROWTH is None:
        _DEFAULT_FPGROWTH = FPGrowthCosavedRecommender()
    return _DEFAULT_FPGROWTH.get_cosaved_recommendations(paper_id=paper_id, top_k=top_k)
