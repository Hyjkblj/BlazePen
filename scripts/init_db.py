"""显式初始化当前项目使用的本地 PostgreSQL 数据库。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


BASELINE_REVISION = "20260317_0001"


def _enable_utf8_console() -> None:
    """在 Windows 终端里尽量保证中文输出正常。"""
    if sys.platform != "win32":
        return

    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")


def _bootstrap_backend_path() -> Path:
    """把 backend 目录加入路径，并切到该目录读取 .env。"""
    backend_dir = Path(__file__).resolve().parent.parent / "backend"
    sys.path.insert(0, str(backend_dir))
    os.chdir(backend_dir)
    return backend_dir


def _build_database_url(config_module, database_name: str | None = None) -> str:
    """拼出数据库连接串，便于脚本统一复用。"""
    db_config = config_module.DB_CONFIG
    target_database = database_name or db_config["database"]
    return (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{target_database}"
    )


def _quote_identifier(identifier: str) -> str:
    """安全引用 PostgreSQL 标识符，避免数据库名包含特殊字符时 SQL 失效。"""
    return '"' + str(identifier).replace('"', '""') + '"'


def ensure_database_exists(config_module) -> tuple[str, bool]:
    """确保目标数据库存在；若不存在则先创建。"""
    database_name = str(config_module.DB_CONFIG["database"])
    admin_url = _build_database_url(config_module, database_name="postgres")
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)

    try:
        with admin_engine.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :database_name"),
                {"database_name": database_name},
            ).scalar()
            if exists:
                return database_name, False

            # 显式创建数据库，把“先建库再建表”收口到同一脚本中。
            connection.execute(text(f"CREATE DATABASE {_quote_identifier(database_name)}"))
            return database_name, True
    finally:
        admin_engine.dispose()


def _build_alembic_config(backend_dir: Path) -> Config:
    """构建 Alembic 配置，统一走正式迁移入口。"""
    alembic_ini = backend_dir / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    return config


def _has_table(engine, table_name: str) -> bool:
    """判断当前数据库是否已经存在指定表。"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def _has_managed_tables(engine) -> bool:
    """判断当前数据库里是否已经存在项目托管的核心业务表。"""
    managed_tables = {
        "characters",
        "character_attributes",
        "character_states",
        "training_sessions",
        "training_rounds",
        "round_evaluations",
        "kt_state_snapshots",
        "narrative_state_snapshots",
        "ending_results",
        "scenario_recommendation_logs",
        "training_audit_events",
        "kt_observations",
    }
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    return bool(managed_tables.intersection(existing_tables))


def migrate_database(database_url: str, backend_dir: Path) -> None:
    """执行数据库迁移。

    规则：
    1. 空库直接 upgrade 到最新版本
    2. 已有业务表但没有 alembic_version 的旧库，先 stamp 到 baseline，再继续 upgrade
    """
    engine = create_engine(database_url, pool_pre_ping=True)
    alembic_config = _build_alembic_config(backend_dir)

    try:
        has_version_table = _has_table(engine, "alembic_version")
        has_managed_tables = _has_managed_tables(engine)

        if not has_version_table and has_managed_tables:
            print(f"ℹ️  检测到已有业务表但未纳入迁移管理，先标记 baseline: {BASELINE_REVISION}")
            command.stamp(alembic_config, BASELINE_REVISION)

        print("开始执行 Alembic 迁移...")
        command.upgrade(alembic_config, "head")
    finally:
        engine.dispose()


def create_database() -> None:
    """创建数据库并通过 Alembic 迁移到最新版本。"""
    _enable_utf8_console()
    backend_dir = _bootstrap_backend_path()

    import config

    database_name, created = ensure_database_exists(config)
    database_url = _build_database_url(config, database_name=database_name)

    print(f"正在连接数据库: {database_url}")
    if created:
        print(f"✅ 数据库不存在，已自动创建: {database_name}")
    else:
        print(f"ℹ️  数据库已存在，继续执行迁移: {database_name}")

    print("开始显式初始化数据库结构...")

    try:
        migrate_database(database_url=database_url, backend_dir=backend_dir)
        engine = create_engine(database_url, pool_pre_ping=True)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        engine.dispose()

        print("✅ PostgreSQL 数据库迁移完成！")
        print(f"   数据库 URL: {database_url}")
        print(f"   表数量: {len(tables)}")
        print()
        print("当前表清单：")
        for table in tables:
            print(f"   - {table}")
        print()
        print("说明：")
        print("1. 当前脚本是本地 PostgreSQL 的显式初始化与迁移入口。")
        print("2. 应用启动时不再自动补表。")
        print("3. 如需检查数据库状态，请执行 `python scripts/check_database_status.py`。")
    except Exception as exc:
        import traceback

        print(f"❌ 数据库初始化失败: {exc}")
        print(f"   错误类型: {type(exc).__name__}")
        print()
        print("完整错误堆栈：")
        traceback.print_exc()
        print()
        print("请检查：")
        print("1. PostgreSQL 服务是否已启动")
        print("2. backend/.env 中的数据库配置是否正确")
        print("3. 当前数据库用户是否有建库与建表权限")
        sys.exit(1)


if __name__ == "__main__":
    create_database()
