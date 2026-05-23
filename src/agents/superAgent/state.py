from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages


@dataclass
class State:
    messages: Annotated[Sequence[AnyMessage], add_messages] = field(default_factory=list)
    original_query: str = ""
    rewritten_query: str = ""
    query_variants: list[str] = field(default_factory=list)
    query_desc: str = ""
    query_img: str = ""
    intent: dict[str, Any] = field(default_factory=dict)
    needs_knowledge: bool = False
    needs_cache: bool = True
    cache_key: str = ""
    cache_hit: dict[str, Any] | None = None
    db_id: str = ""
    retrieval_results: list[dict[str, Any]] = field(default_factory=list)
    memory_summary: str = ""
    recent_turns: list[dict[str, str]] = field(default_factory=list)
    answer_text: str = ""
    answer_source: str = ""
    summary_due: bool = False
