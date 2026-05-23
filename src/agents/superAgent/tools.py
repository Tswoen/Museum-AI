from typing import Any

from src.agents.chatbot.tools import get_tools as get_chatbot_tools


def get_tools() -> list[Any]:
    """获取超级智能体可用的工具。"""
    return get_chatbot_tools()
