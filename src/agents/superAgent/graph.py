from __future__ import annotations

import asyncio
import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from src import config as sys_config
from src.agents.common.base import BaseAgent
from src.agents.common.mcp import get_mcp_tools
from src.agents.common.models import load_chat_model
from src.chatflow.intent import classify_query
from src.utils import logger

from .cache import AnswerCache
from .context import Context
from .memory import SuperMemoryStore
from .retrieval import RetrievalService
from .state import State
from .tools import get_tools

SUPER_AGENT_STATIC_PROMPT = """You are the Museum-AI SuperAgent.

Role & Policies:
- Answer as a museum-domain assistant.
- Prefer evidence from retrieval results over guesswork.
- Keep answers concise, factual, and structured.
- If the evidence is weak, say so clearly instead of inventing details.

Workflow:
1. Rewrite the user's question into one clean search query.
2. Build a few short query variants for multi-query retrieval.
3. Check memory summary and recent turns before answering.
4. Use retrieved evidence only when needed.
5. Use tools when they are genuinely useful.

Output:
- Be direct.
- Preserve named entities and key facts.
- Avoid repeating raw retrieval noise.

Examples:
- User: "这件器物是什么时期的？"
  Search: "器物 年代 断代"
- User: "结合上下文继续说"
  Search: "继续 上下文 总结"
"""


@dataclass
class RewritePlan:
    rewritten_query: str = ""
    query_variants: list[str] = field(default_factory=list)
    query_desc: str = ""
    query_img: str = ""
    needs_knowledge: bool = False
    needs_cache: bool = True


class SuperAgent(BaseAgent):
    name = "超级智能助手"
    description = "具备查询改写、预检索、工具调用、缓存和异步记忆总结能力的增强型博物馆助手。"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.graph = None
        self.checkpointer = None
        self.context_schema = Context
        self.agent_tools = None
        self.cache = AnswerCache()
        self.memory_store = SuperMemoryStore()
        self.retrieval = RetrievalService(default_db_id=getattr(sys_config, "default_database_id", None))

    def get_tools(self):
        return get_tools()

    async def _get_invoke_tools(self, selected_tools: list[str], selected_mcps: list[str]):
        """根据配置获取可用工具。"""
        enabled_tools = []
        self.agent_tools = self.agent_tools or self.get_tools()

        if selected_tools and isinstance(selected_tools, list):
            enabled_tools = [tool for tool in self.agent_tools if tool.name in selected_tools]

        if selected_mcps and isinstance(selected_mcps, list):
            for mcp in selected_mcps:
                enabled_tools.extend(await get_mcp_tools(mcp))

        return enabled_tools

    def _extract_images(self, query: str) -> list[str]:
        image_pattern = r"https?://[^\s]+?\.(?:png|jpg|jpeg|webp|gif|bmp)"
        return re.findall(image_pattern, query or "", flags=re.IGNORECASE)

    def _normalize_query_text(self, query: str) -> str:
        cleaned = (query or "").strip()
        cleaned = cleaned.replace("[图片附件地址]:", "").strip()
        cleaned = re.sub(r"https?://[^\s]+", "", cleaned, flags=re.IGNORECASE).strip()
        return cleaned or query.strip()

    def _count_human_turns(self, messages) -> int:
        return self.memory_store.count_human_turns(messages)

    def _build_recent_turns_block(self, recent_turns: list[dict[str, str]]) -> str:
        if not recent_turns:
            return ""
        lines = ["短期记忆:"]
        for turn in recent_turns:
            lines.append(f"{turn['role']}: {turn['content']}")
        return "\n".join(lines)

    def _build_retrieval_block(self, retrieval_results: list[dict[str, Any]]) -> str:
        if not retrieval_results:
            return ""
        lines = ["检索证据:"]
        for item in retrieval_results[:8]:
            content = item.get("content", "")
            source = item.get("source", "knowledge_base")
            score = item.get("score", 0.0)
            lines.append(f"- [{source}] {content} (score={score:.2f})")
        return "\n".join(lines)

    def _build_system_prompt(self, runtime: Runtime[Context], state: State) -> str:
        parts = [runtime.context.system_prompt or "You are a helpful assistant.", SUPER_AGENT_STATIC_PROMPT]
        memory_summary = state.memory_summary or ""
        recent_turns_block = self._build_recent_turns_block(state.recent_turns)
        retrieval_block = self._build_retrieval_block(state.retrieval_results)

        if memory_summary:
            parts.append(f"长期记忆摘要:\n{memory_summary}")
        if recent_turns_block:
            parts.append(recent_turns_block)
        if retrieval_block:
            parts.append(retrieval_block)
        if state.rewritten_query:
            parts.append(f"改写后的问题: {state.rewritten_query}")
        if state.query_variants:
            parts.append("多查询变体:\n" + "\n".join(f"- {item}" for item in state.query_variants))

        return "\n\n".join(part for part in parts if part)

    def _extract_json_object(self, text: str) -> dict[str, Any]:
        if not text:
            return {}

        cleaned = text.strip()
        try:
            return json.loads(cleaned)
        except Exception:
            pass

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(cleaned[start : end + 1])
            except Exception:
                return {}

        return {}

    def _make_cache_key(self, query: str, db_id: str | None, mode: str) -> str:
        payload = {"q": query.strip().lower(), "db": db_id or "", "mode": mode}
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def _rewrite_query_node(self, state: State, runtime: Runtime[Context]) -> dict[str, Any]:
        original_query = self._normalize_query_text(state.messages[-1].content if state.messages else "")
        image_urls = self._extract_images(original_query)
        query_for_classification = original_query

        intent = classify_query(query_for_classification, image_urls)
        memory_snapshot = self.memory_store.build_snapshot(
            state.messages,
            runtime.context.thread_id,
            max_turns=max(runtime.context.summary_turns, 1),
        )

        plan = RewritePlan(
            rewritten_query=original_query,
            query_variants=[original_query],
            query_desc=intent.query_desc or original_query,
            query_img=intent.query_img or (image_urls[0] if image_urls else ""),
            needs_knowledge=intent.needs_knowledge,
            needs_cache=intent.needs_cache and runtime.context.cache_enabled,
        )

        if runtime.context.rewrite_enabled and original_query:
            rewrite_model_spec = runtime.context.rewrite_model or runtime.context.model
            try:
                model = load_chat_model(rewrite_model_spec)
                prompt = (
                    "请把用户问题改写成适合检索的短查询，并输出 JSON。\n"
                    "必须包含字段: rewritten_query, query_variants, needs_knowledge, query_desc, query_img。\n"
                    "query_variants 至少给出 2 个简洁变体，保留实体名和时间信息。\n"
                    "如果是闲聊或观点类问题，needs_knowledge 设为 false。\n"
                    f"用户问题: {original_query}"
                )
                response = await model.ainvoke(
                    [SystemMessage(content=prompt), HumanMessage(content=original_query)],
                )
                payload = self._extract_json_object(getattr(response, "content", ""))
                if payload:
                    plan.rewritten_query = str(payload.get("rewritten_query") or plan.rewritten_query).strip() or original_query
                    variants = payload.get("query_variants") or []
                    if isinstance(variants, list):
                        plan.query_variants = self.retrieval._unique_queries([plan.rewritten_query, *map(str, variants), original_query])
                    plan.needs_knowledge = bool(payload.get("needs_knowledge", plan.needs_knowledge))
                    plan.query_desc = str(payload.get("query_desc") or plan.query_desc or original_query)
                    plan.query_img = str(payload.get("query_img") or plan.query_img or "")
            except Exception as exc:
                logger.warning(f"Query rewrite failed, fallback to original query: {exc}")

        query_variants = self.retrieval._unique_queries([plan.rewritten_query, *plan.query_variants, original_query])
        cache_key = self._make_cache_key(plan.rewritten_query or original_query, state.db_id or None, runtime.context.retrieval_mode)

        return {
            "original_query": original_query,
            "rewritten_query": plan.rewritten_query or original_query,
            "query_variants": query_variants,
            "query_desc": plan.query_desc or original_query,
            "query_img": plan.query_img or "",
            "intent": asdict(intent),
            "needs_knowledge": plan.needs_knowledge,
            "needs_cache": plan.needs_cache,
            "cache_key": cache_key,
            "memory_summary": memory_snapshot.summary,
            "recent_turns": memory_snapshot.recent_turns,
            "db_id": self.retrieval.resolve_db_id(state.db_id or None) or "",
        }

    async def _cache_lookup_node(self, state: State, runtime: Runtime[Context]) -> dict[str, Any]:
        if not runtime.context.cache_enabled or not state.needs_cache:
            return {}

        cache_key = state.cache_key or self._make_cache_key(state.rewritten_query or state.original_query, state.db_id or None, runtime.context.retrieval_mode)
        cached = self.cache.get(cache_key)
        if not cached:
            return {"cache_hit": None}

        return {
            "cache_hit": cached,
            "answer_text": cached.get("answer", ""),
            "answer_source": "cache",
        }

    def _route_after_cache_lookup(self, state: State) -> str:
        if state.cache_hit:
            return "hit"
        return "miss"

    async def _retrieval_node(self, state: State, runtime: Runtime[Context]) -> dict[str, Any]:
        if not state.needs_knowledge:
            return {"retrieval_results": []}

        db_id = self.retrieval.resolve_db_id(state.db_id or None)
        if not db_id:
            return {"retrieval_results": []}

        results = await self.retrieval.search(
            query_text=state.rewritten_query or state.original_query,
            db_id=db_id,
            query_variants=state.query_variants,
            query_img=state.query_img,
            query_desc=state.query_desc,
            mode=runtime.context.retrieval_mode,
            top_k=max(int(runtime.context.top_k or 5), 1),
        )

        return {"retrieval_results": results, "db_id": db_id}

    async def _chat_node(self, state: State, runtime: Runtime[Context]) -> dict[str, Any]:
        model = load_chat_model(runtime.context.model)
        available_tools = await self._get_invoke_tools(runtime.context.tools, runtime.context.mcps)
        if available_tools:
            model = model.bind_tools(available_tools)

        if state.cache_hit:
            response = AIMessage(content=state.cache_hit.get("answer", ""), response_metadata={"source": "cache"})
        else:
            system_prompt = self._build_system_prompt(runtime, state)
            response = cast(
                AIMessage,
                await model.ainvoke([SystemMessage(content=system_prompt), *state.messages]),
            )

        return {
            "messages": [response],
            "answer_text": getattr(response, "content", ""),
            "answer_source": state.answer_source or "model",
        }

    async def dynamic_tools_node(self, state: State, runtime: Runtime[Context]) -> dict[str, list[ToolMessage]]:
        available_tools = await self._get_invoke_tools(runtime.context.tools, runtime.context.mcps)
        tool_node = ToolNode(available_tools)
        result = await tool_node.ainvoke(state)
        return cast(dict[str, list[ToolMessage]], result)

    def _route_after_chat(self, state: State) -> str:
        if not state.messages:
            return "summary"

        last_message = state.messages[-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"

        return "summary"

    async def _summary_node(self, state: State, runtime: Runtime[Context]) -> dict[str, Any]:
        thread_id = runtime.context.thread_id

        if state.answer_text and state.needs_cache and runtime.context.cache_enabled and state.answer_source != "cache":
            self.cache.set(
                state.cache_key or self._make_cache_key(state.rewritten_query or state.original_query, state.db_id or None, runtime.context.retrieval_mode),
                {
                    "answer": state.answer_text,
                    "references": state.retrieval_results[:3],
                },
            )

        if not thread_id or not runtime.context.summary_enabled:
            return {}

        human_turns = self._count_human_turns(state.messages)
        if human_turns <= 0 or human_turns % max(int(runtime.context.summary_turns or 5), 1) != 0:
            return {}

        recent_turns = self.memory_store.extract_recent_turns(state.messages, max_turns=max(int(runtime.context.summary_turns or 5), 1))
        previous_summary = self.memory_store.get_summary(thread_id)
        summary_model_spec = runtime.context.summary_model or runtime.context.rewrite_model or runtime.context.model

        asyncio.create_task(
            self._update_summary_async(
                thread_id=thread_id,
                previous_summary=previous_summary,
                recent_turns=recent_turns,
                model_spec=summary_model_spec,
            )
        )

        return {"summary_due": True}

    async def _update_summary_async(
        self,
        *,
        thread_id: str,
        previous_summary: str,
        recent_turns: list[dict[str, str]],
        model_spec: str,
    ) -> None:
        try:
            model = load_chat_model(model_spec)
            turn_block = "\n".join(f"{turn['role']}: {turn['content']}" for turn in recent_turns)
            prompt = (
                "请根据下面的对话片段更新长期记忆摘要，要求保留用户偏好、关键事实、未完成任务和实体名。"
                "输出要简洁，使用中文。\n"
                f"已有摘要:\n{previous_summary or '无'}\n\n"
                f"新对话片段:\n{turn_block}\n\n"
                "只输出更新后的摘要。"
            )
            response = await model.ainvoke([SystemMessage(content=prompt)])
            summary_text = str(getattr(response, "content", "")).strip()
            if summary_text:
                self.memory_store.update_summary(thread_id, summary_text)
        except Exception as exc:
            logger.warning(f"Async memory summary failed for {thread_id}: {exc}")

    async def get_graph(self, **kwargs):
        if self.graph:
            return self.graph

        builder = StateGraph(State, context_schema=self.context_schema)
        builder.add_node("rewrite", self._rewrite_query_node)
        builder.add_node("cache_lookup", self._cache_lookup_node)
        builder.add_node("retrieve", self._retrieval_node)
        builder.add_node("chat", self._chat_node)
        builder.add_node("tools", self.dynamic_tools_node)
        builder.add_node("summary", self._summary_node)

        builder.add_edge(START, "rewrite")
        builder.add_edge("rewrite", "cache_lookup")
        builder.add_conditional_edges("cache_lookup", self._route_after_cache_lookup, {"hit": "chat", "miss": "retrieve"})
        builder.add_edge("retrieve", "chat")
        builder.add_conditional_edges("chat", self._route_after_chat, {"tools": "tools", "summary": "summary"})
        builder.add_edge("tools", "chat")
        builder.add_edge("summary", END)

        self.checkpointer = await self._get_checkpointer()
        graph = builder.compile(checkpointer=self.checkpointer, name=self.name)
        self.graph = graph
        logger.info("SuperAgent graph compiled successfully")
        return graph
