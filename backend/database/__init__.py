"""数据库模块。

这里避免在包导入阶段就连带拉起向量数据库和其重依赖，
让训练域这类只需要结构化存储的代码可以轻量导入。
"""

from __future__ import annotations

from .db_manager import DatabaseManager

__all__ = ["DatabaseManager", "VectorDatabase"]


def __getattr__(name: str):
    """按需延迟导入可选组件，避免非训练依赖污染训练域测试。"""
    if name == "VectorDatabase":
        from .vector_db import VectorDatabase

        return VectorDatabase
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
