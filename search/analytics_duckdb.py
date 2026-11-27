"""
DuckDB Columnar OLAP Analytics Engine for Research Commons
Implements dimensional modeling (star schema) over activity logs and papers
to deliver sub-second administrative queries for the Institutional Analytics Dashboard (F9).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

try:
    import duckdb  # type: ignore
    DUCKDB_AVAILABLE = True
except ImportError:
    duckdb = None
    DUCKDB_AVAILABLE = False


class DuckDBAnalytics:
    """
    Columnar analytics engine powered by DuckDB.
    Constructs an in-memory Star Schema data mart (facts + dimensions)
    from synthetic/operational data and provides fast OLAP queries.
    """

    def __init__(self, db_path: str = ":memory:") -> None:
        self.db_path = db_path
        self.con: Any = None
        self._init_connection()

    def _init_connection(self) -> None:
        if DUCKDB_AVAILABLE:
            self.con = duckdb.connect(database=self.db_path)

    def load_data(
        self,
        papers: list[dict[str, Any]],
        users: list[dict[str, Any]],
        posts: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> DuckDBAnalytics:
        """
        Builds the star schema inside DuckDB:
        - dim_paper (paper metadata, topic, publication year)
        - dim_user (user department, role, name)
        - fact_events (10,000+ views, saves, searches over 6 months)
        - fact_posts (community discussions and engagement)
        """
        if not DUCKDB_AVAILABLE or self.con is None:
            return self

        # 1. Prepare dimension tables
        paper_rows = []
        for p in papers:
            concepts = p.get("concepts", [])
            primary_topic = concepts[0] if concepts else p.get("department_topic", "General")
            paper_rows.append({
                "paper_id": str(p["id"]),
                "title": p.get("title", ""),
                "primary_topic": primary_topic,
                "publication_year": p.get("publication_year") or 2024,
                "citation_count": p.get("citation_count") or 0,
            })

        user_rows = []
        for u in users:
            user_rows.append({
                "user_id": int(u["id"]),
                "name": u.get("name", ""),
                "department": u.get("department", "Unassigned"),
                "role": u.get("role", "student"),
            })

        # 2. Prepare fact tables
        event_rows = []
        for ev in events:
            dt_str = ev.get("timestamp", "")
            date_only = dt_str[:10] if dt_str else "2026-06-01"
            event_rows.append({
                "event_id": ev.get("id"),
                "user_id": int(ev.get("user_id", 0)),
                "event_type": ev.get("event_type", "view"),
                "target_id": str(ev.get("target_id") or ""),
                "query_text": ev.get("query_text") or "",
                "event_date": date_only,
                "timestamp": dt_str,
            })

        post_rows = []
        for pt in posts:
            post_rows.append({
                "post_id": pt.get("id"),
                "user_id": int(pt.get("user_id", 0)),
                "attached_paper_id": str(pt.get("attached_paper_id") or ""),
                "created_at": pt.get("created_at", ""),
            })

        # Register and create tables in DuckDB
        self.con.execute("CREATE OR REPLACE TABLE dim_paper AS SELECT * FROM paper_rows")
        self.con.execute("CREATE OR REPLACE TABLE dim_user AS SELECT * FROM user_rows")
        self.con.execute("CREATE OR REPLACE TABLE fact_events AS SELECT * FROM event_rows")
        self.con.execute("CREATE OR REPLACE TABLE fact_posts AS SELECT * FROM post_rows")

        return self

    def get_research_topics_by_department(self) -> list[dict[str, Any]]:
        """
        F9: Breakdown of most active research topics across departments.
        Calculated from paper bookmarks and searches.
        """
        if not DUCKDB_AVAILABLE or self.con is None:
            return []

        query = """
        SELECT 
            u.department,
            p.primary_topic,
            COUNT(*) as interaction_count,
            COUNT(DISTINCT u.user_id) as unique_researchers
        FROM fact_events e
        JOIN dim_user u ON e.user_id = u.user_id
        JOIN dim_paper p ON e.target_id = p.paper_id
        WHERE e.event_type IN ('view', 'save')
        GROUP BY u.department, p.primary_topic
        ORDER BY u.department, interaction_count DESC
        """
        df = self.con.execute(query).fetchdf()
        return df.to_dict(orient="records")

    def get_department_collaboration_matrix(self) -> list[dict[str, Any]]:
        """
        F9: Inter-department collaboration indicator.
        Measures how often researchers in Department A interact with papers 
        or discuss topics associated with Department B.
        """
        if not DUCKDB_AVAILABLE or self.con is None:
            return []

        query = """
        SELECT 
            u.department as researcher_department,
            p.primary_topic as topic_area,
            COUNT(*) as engagement_volume
        FROM fact_events e
        JOIN dim_user u ON e.user_id = u.user_id
        JOIN dim_paper p ON e.target_id = p.paper_id
        GROUP BY u.department, p.primary_topic
        ORDER BY engagement_volume DESC
        LIMIT 25
        """
        df = self.con.execute(query).fetchdf()
        return df.to_dict(orient="records")

    def get_most_saved_and_discussed_papers(self, top_n: int = 10) -> list[dict[str, Any]]:
        """
        F9: Top papers by cumulative community saves, views, and post mentions.
        """
        if not DUCKDB_AVAILABLE or self.con is None:
            return []

        query = f"""
        SELECT 
            p.paper_id,
            p.title,
            p.primary_topic,
            p.citation_count as academic_citations,
            SUM(CASE WHEN e.event_type = 'save' THEN 1 ELSE 0 END) as library_saves,
            SUM(CASE WHEN e.event_type = 'view' THEN 1 ELSE 0 END) as member_views,
            COUNT(DISTINCT post.post_id) as forum_discussions
        FROM dim_paper p
        LEFT JOIN fact_events e ON p.paper_id = e.target_id
        LEFT JOIN fact_posts post ON p.paper_id = post.attached_paper_id
        GROUP BY p.paper_id, p.title, p.primary_topic, p.citation_count
        ORDER BY library_saves DESC, member_views DESC
        LIMIT {top_n}
        """
        df = self.con.execute(query).fetchdf()
        return df.to_dict(orient="records")

    def get_engagement_trends_over_time(self) -> list[dict[str, Any]]:
        """
        F9: Monthly and weekly engagement trends (view/save/search activity).
        """
        if not DUCKDB_AVAILABLE or self.con is None:
            return []

        query = """
        SELECT 
            SUBSTRING(event_date, 1, 7) as year_month,
            event_type,
            COUNT(*) as total_events
        FROM fact_events
        GROUP BY year_month, event_type
        ORDER BY year_month, event_type
        """
        df = self.con.execute(query).fetchdf()
        return df.to_dict(orient="records")

    def get_drill_down_stats(
        self,
        department: str | None = None,
        topic: str | None = None,
    ) -> dict[str, Any]:
        """
        F9: Drill-down from university -> department -> topic -> member.
        """
        if not DUCKDB_AVAILABLE or self.con is None:
            return {}

        where_clauses = ["1=1"]
        if department:
            where_clauses.append(f"u.department = '{department}'")
        if topic:
            where_clauses.append(f"p.primary_topic = '{topic}'")

        where_sql = " AND ".join(where_clauses)

        summary_query = f"""
        SELECT 
            COUNT(DISTINCT u.user_id) as active_members,
            COUNT(DISTINCT p.paper_id) as unique_papers_engaged,
            COUNT(e.event_id) as total_interactions
        FROM fact_events e
        JOIN dim_user u ON e.user_id = u.user_id
        LEFT JOIN dim_paper p ON e.target_id = p.paper_id
        WHERE {where_sql}
        """
        summary = self.con.execute(summary_query).fetchone()

        return {
            "department": department or "All Departments",
            "topic": topic or "All Topics",
            "active_members": summary[0] if summary else 0,
            "unique_papers_engaged": summary[1] if summary else 0,
            "total_interactions": summary[2] if summary else 0,
        }

    def get_topic_hierarchical_clustering(
        self,
        papers: list[dict[str, Any]] | None = None,
        k_clusters: int = 4,
    ) -> dict[str, Any]:
        """
        F9: Hierarchical Agglomerative Clustering of Research Topics.
        Builds topic co-occurrence across papers, normalizes into cosine distance matrix,
        computes linkage using average/UPGMA method, and cuts tree at k clusters.
        """
        from collections import Counter, defaultdict
        import numpy as np

        try:
            from scipy.cluster.hierarchy import linkage, fcluster
            from scipy.spatial.distance import squareform
            has_scipy = True
        except ImportError:
            has_scipy = False

        # Gather topic frequencies from papers or dim_paper
        paper_topics: list[list[str]] = []
        if papers:
            for p in papers:
                concepts = p.get("concepts", [])
                c_names = []
                if isinstance(concepts, list):
                    for c in concepts:
                        name = c if isinstance(c, str) else (c.get("name") or c.get("display_name") or "")
                        if name and len(name) > 2:
                            c_names.append(name.strip().title())
                dept = p.get("department_topic")
                if dept:
                    c_names.append(dept.strip().title())
                if c_names:
                    paper_topics.append(list(set(c_names)))
        elif self.con:
            rows = self.con.execute("SELECT primary_topic FROM dim_paper WHERE primary_topic IS NOT NULL").fetchall()
            paper_topics = [[r[0].title()] for r in rows if r[0]]

        if not paper_topics:
            return {"total_topics": 0, "clusters": [], "dendrogram_nodes": []}

        topic_counts = Counter()
        for ts in paper_topics:
            topic_counts.update(ts)

        top_topics = [t for t, _ in topic_counts.most_common(16)]
        if len(top_topics) < 3 or not has_scipy:
            # Fallback simple partition
            clusters_fallback = [
                {"cluster_id": 1, "name": "AI & Machine Learning", "topics": top_topics[:4], "count": 4},
                {"cluster_id": 2, "name": "Data Systems & Cloud", "topics": top_topics[4:8], "count": 4},
                {"cluster_id": 3, "name": "Computational Biology", "topics": top_topics[8:], "count": len(top_topics[8:])},
            ]
            return {"total_topics": len(top_topics), "clusters": clusters_fallback, "method": "heuristic"}

        topic_to_idx = {t: i for i, t in enumerate(top_topics)}
        n = len(top_topics)
        co_matrix = np.zeros((n, n), dtype=float)

        for ts in paper_topics:
            sub = [t for t in ts if t in topic_to_idx]
            for i in range(len(sub)):
                for j in range(len(sub)):
                    co_matrix[topic_to_idx[sub[i]], topic_to_idx[sub[j]]] += 1

        norms = np.sqrt(np.diag(co_matrix))
        norms[norms == 0] = 1e-9
        corr = co_matrix / np.outer(norms, norms)
        dist_matrix = np.clip(1.0 - corr, 0.0, 2.0)
        np.fill_diagonal(dist_matrix, 0.0)

        condensed = squareform(dist_matrix, checks=False)
        Z = linkage(condensed, method="average")
        cluster_labels = fcluster(Z, t=min(k_clusters, n - 1), criterion="maxclust")

        cluster_map = defaultdict(list)
        for topic, cid in zip(top_topics, cluster_labels):
            cluster_map[int(cid)].append({
                "topic": topic,
                "frequency": int(topic_counts[topic]),
            })

        cluster_names = [
            "AI & Data Mining Systems",
            "Distributed & Cloud Networks",
            "Bioinformatics & Life Sciences",
            "Software & Computational Theory",
            "Applied Mathematics & Modeling",
        ]

        formatted_clusters = []
        for cid, t_items in cluster_map.items():
            name_idx = (cid - 1) % len(cluster_names)
            formatted_clusters.append({
                "cluster_id": cid,
                "name": cluster_names[name_idx],
                "topics": [item["topic"] for item in t_items],
                "details": t_items,
                "paper_volume": sum(item["frequency"] for item in t_items),
            })

        formatted_clusters.sort(key=lambda c: c["paper_volume"], reverse=True)

        return {
            "total_topics": len(top_topics),
            "algorithm": "Agglomerative Hierarchical Clustering (Average Linkage / UPGMA)",
            "clusters": formatted_clusters,
            "linkage_matrix_steps": len(Z),
        }
