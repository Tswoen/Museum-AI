from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src import graph_base, knowledge_base
from src.utils import logger


@dataclass
class RetrievalService:
    default_db_id: str | None = None
    last_results: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    def resolve_db_id(self, candidate: str | None = None) -> str | None:
        if candidate or self.default_db_id:
            return candidate or self.default_db_id

        try:
            databases = knowledge_base.get_databases().get("databases", [])
        except Exception:
            return None

        if not databases:
            return None

        return databases[0].get("db_id")

    async def search(
        self,
        query_text: str,
        db_id: str | None,
        query_variants: list[str] | None = None,
        query_img: str = "",
        query_desc: str = "",
        mode: str = "mix",
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        target_db_id = self.resolve_db_id(db_id)
        if not target_db_id:
            return []

        queries = self._unique_queries([query_text, *(query_variants or [])])
        results: list[dict[str, Any]] = []

        for query in queries:
            try:
                query_kwargs: dict[str, Any] = {"top_k": top_k, "mode": mode}
                if query_img:
                    query_kwargs["img_path"] = query_img
                if query_desc:
                    query_kwargs["query_desc"] = query_desc

                kb_results = await knowledge_base.aquery(query_text=query, db_id=target_db_id, **query_kwargs)
                results.extend(self._normalize_results(kb_results, source="knowledge_base", query=query))
            except Exception as exc:
                logger.warning(f"Knowledge base search failed for '{query}': {exc}")

        try:
            graph_results = graph_base.query_node(queries[0] if queries else query_text, hops=2, return_format="triples")
            results.extend(self._normalize_graph_results(graph_results))
        except Exception as exc:
            logger.warning(f"Knowledge graph search failed: {exc}")

        deduped = self._dedupe_results(results)
        self.last_results[target_db_id] = deduped
        return deduped[: max(top_k * 3, top_k)]

    def _unique_queries(self, queries: list[str]) -> list[str]:
        unique: list[str] = []
        seen = set()
        for query in queries:
            text = (query or "").strip()
            if not text or text in seen:
                continue
            unique.append(text)
            seen.add(text)
        return unique

    def _normalize_results(self, results, source: str, query: str) -> list[dict[str, Any]]:
        if not results:
            return []
        if isinstance(results, str):
            return [{"content": results, "metadata": {"source": source, "query": query}, "score": 1.0, "source": source}]
        if isinstance(results, dict):
            return [
                {
                    "content": results.get("content") or str(results),
                    "metadata": results.get("metadata", {}) | {"source": source, "query": query},
                    "score": results.get("score", 0.0),
                    "source": source,
                }
            ]

        normalized = []
        for item in results:
            if isinstance(item, dict):
                normalized.append(
                    {
                        "content": item.get("content") or str(item),
                        "metadata": item.get("metadata", {}) | {"source": source, "query": query},
                        "score": item.get("score", item.get("similarity", 0.0)),
                        "source": source,
                    }
                )
            else:
                normalized.append({"content": str(item), "metadata": {"source": source, "query": query}, "score": 0.0, "source": source})

        return normalized

    def _normalize_graph_results(self, results) -> list[dict[str, Any]]:
        if not results:
            return []

        triples = results.get("triples") if isinstance(results, dict) else None
        if not triples:
            return []

        normalized = []
        for triple in triples:
            if not triple or len(triple) != 3:
                continue
            head, rel, tail = triple
            normalized.append(
                {
                    "content": f"{head} -[{rel}]-> {tail}",
                    "metadata": {"source": "knowledge_graph", "triple": triple},
                    "score": 0.7,
                    "source": "knowledge_graph",
                }
            )
        return normalized

    def _dedupe_results(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        deduped: list[dict[str, Any]] = []
        seen = set()
        for item in results:
            key = item.get("metadata", {}).get("chunk_id") or item.get("content")
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped
