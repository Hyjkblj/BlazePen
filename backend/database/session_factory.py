"""数据库连接工厂。

把 PostgreSQL 连接配置和 SQLAlchemy engine/sessionmaker 的创建集中到这里，
避免不同领域各自拼接连接串，后续切换连接策略时只改一处。
"""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

import config


def build_database_url(database_name: str | None = None) -> str:
    """根据配置拼出 PostgreSQL 连接串。"""
    db_config = config.DB_CONFIG
    target_database = database_name or db_config["database"]
    return (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{target_database}"
    )


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """返回进程级共享 engine，统一复用连接池。"""
    return create_engine(build_database_url(), pool_pre_ping=True)


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker:
    """返回进程级共享 sessionmaker。"""
    return sessionmaker(bind=get_engine(), expire_on_commit=False)
