from dataclasses import dataclass, field
from typing import Annotated

from src.agents.common.context import BaseContext
from src.agents.common.mcp import MCP_SERVERS
from src.agents.common.tools import gen_tool_info

from .tools import get_tools


@dataclass(kw_only=True)
class Context(BaseContext):
    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="siliconflow/Qwen/Qwen3-235B-A22B-Instruct-2507",
        metadata={"name": "主模型", "options": [], "description": "用于最终回答的模型"},
    )

    rewrite_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="siliconflow/Qwen/Qwen3-8B",
        metadata={"name": "改写模型", "options": [], "description": "用于查询改写与多查询扩展的轻量模型"},
    )

    summary_model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="siliconflow/Qwen/Qwen3-8B",
        metadata={"name": "总结模型", "options": [], "description": "用于异步记忆总结的轻量模型"},
    )

    tools: Annotated[list[dict], {"__template_metadata__": {"kind": "tools"}}] = field(
        default_factory=list,
        metadata={
            "name": "工具",
            "options": gen_tool_info(get_tools()),
            "description": "可用工具列表",
        },
    )

    mcps: list[str] = field(
        default_factory=list,
        metadata={"name": "MCP服务", "options": list(MCP_SERVERS.keys()), "description": "MCP 服务列表"},
    )

    retrieval_mode: str = field(
        default="mix",
        metadata={
            "name": "检索模式",
            "options": ["mix", "local", "global", "hybrid", "naive"],
            "description": "知识库检索模式",
        },
    )

    top_k: int = field(
        default=5,
        metadata={"name": "检索条数", "description": "每轮检索返回的结果数量"},
    )

    summary_turns: int = field(
        default=5,
        metadata={"name": "总结轮数", "description": "每多少轮对话触发一次异步总结"},
    )

    cache_enabled: bool = field(
        default=True,
        metadata={"name": "启用缓存", "description": "是否启用问答缓存"},
    )

    rewrite_enabled: bool = field(
        default=True,
        metadata={"name": "启用改写", "description": "是否启用查询改写与多查询检索"},
    )

    summary_enabled: bool = field(
        default=True,
        metadata={"name": "启用总结", "description": "是否启用异步记忆总结"},
    )
