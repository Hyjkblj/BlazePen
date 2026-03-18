"""Alembic 环境配置。

这里把 backend 目录加入导入路径，并显式读取 backend/.env，
确保无论从项目根目录还是 backend 目录执行迁移，都使用同一套数据库配置。
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

backend_dir = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

import config as app_config  # noqa: E402
from models.character import Base  # noqa: E402
import models.training  # noqa: F401,E402 - 确保训练模型已注册到 Base.metadata


def _build_database_url() -> str:
    """从项目统一配置生成迁移使用的数据库连接串。"""
    db_config = app_config.DB_CONFIG
    return (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )


config.set_main_option("sqlalchemy.url", _build_database_url())
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线迁移模式。"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线迁移模式。"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
