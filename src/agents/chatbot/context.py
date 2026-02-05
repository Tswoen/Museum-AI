from dataclasses import dataclass, field
from typing import Annotated

from src.agents.common.context import BaseContext
from src.agents.common.mcp import MCP_SERVERS
from src.agents.common.tools import gen_tool_info

from .tools import get_tools

# @dataclass会自动帮你生成 __init__、__repr__、__eq__ 等常用方法，不用手动写。
# kw_only=True参数会强制该数据类的实例化必须使用关键字参数
@dataclass(kw_only=True)
class Context(BaseContext):
    model: Annotated[str, {"__template_metadata__": {"kind": "llm"}}] = field(
        default="siliconflow/Qwen/Qwen3-235B-A22B-Instruct-2507",
        metadata={"name": "智能体模型", "options": [], "description": "智能体的驱动模型"},
    )

    tools: Annotated[list[dict], {"__template_metadata__": {"kind": "tools"}}] = field(
        default_factory=list,
        metadata={
            "name": "工具",
            "options": gen_tool_info(get_tools()),  # 这里的选择是所有的工具
            "description": "工具列表",
        },
    )

    mcps: list[str] = field(
        default_factory=list,
        metadata={"name": "MCP服务器", "options": list(MCP_SERVERS.keys()), "description": "MCP服务器列表"},
    )
