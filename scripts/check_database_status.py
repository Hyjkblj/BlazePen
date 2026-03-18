"""检查当前项目数据库与可选向量库状态。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import inspect, text


CORE_TABLES = [
    "characters",
    "character_attributes",
    "character_states",
]

LEGACY_GAMEPLAY_TABLES = [
    "users",
    "threads",
    "story_states",
    "conversations",
    "image_cache",
]

TRAINING_TABLES = [
    "training_sessions",
    "training_rounds",
    "round_evaluations",
    "kt_state_snapshots",
    "narrative_state_snapshots",
    "scenario_recommendation_logs",
    "training_audit_events",
    "kt_observations",
    "ending_results",
]


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


def _build_database_url(config_module) -> str:
    """拼出当前数据库连接串，便于输出诊断信息。"""
    db_config = config_module.DB_CONFIG
    return (
        f"postgresql://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )


def _print_table_group_status(connection, tables: list[str], group_name: str) -> bool:
    """按分组输出表状态，并返回该分组是否完整。"""
    print(f"【{group_name}】")
    complete = True
    for table in tables:
        result = connection.execute(text(f"SELECT to_regclass('{table}')"))
        exists = result.scalar() is not None
        if not exists:
            print(f"   ✗ {table}")
            complete = False
            continue

        count = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
        print(f"   ✓ {table:32s} (记录数: {count})")
    print()
    return complete


def _print_alembic_status(connection) -> None:
    """输出当前数据库迁移版本，便于确认 schema 是否受控。"""
    result = connection.execute(text("SELECT to_regclass('alembic_version')"))
    exists = result.scalar() is not None
    if not exists:
        print("【迁移状态】")
        print("   ⚠️  alembic_version 表不存在，当前数据库尚未纳入正式迁移管理。")
        print()
        return

    version_num = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    print("【迁移状态】")
    print(f"   ✓ alembic_version               (当前版本: {version_num})")
    print()


def check_postgresql_status():
    """检查 PostgreSQL 连接和表状态。"""
    import config
    from database.db_manager import DatabaseManager

    manager = DatabaseManager()
    database_url = _build_database_url(config)

    print("=" * 60)
    print("数据库状态检测")
    print("=" * 60)
    print()
    print("【1】PostgreSQL 数据库状态")
    print("-" * 60)

    try:
        with manager.engine.connect() as connection:
            version = connection.execute(text("SELECT version()")).scalar()
            inspector = inspect(manager.engine)
            tables = inspector.get_table_names()

            print("✅ 连接成功")
            print(f"   数据库版本: {str(version).split(',')[0]}")
            print(f"   连接 URL: {database_url}")
            print(f"   当前表数量: {len(tables)}")
            print()

            _print_alembic_status(connection)
            core_ready = _print_table_group_status(connection, CORE_TABLES, "角色域表")
            legacy_ready = _print_table_group_status(connection, LEGACY_GAMEPLAY_TABLES, "旧剧情流核心表")
            training_ready = _print_table_group_status(connection, TRAINING_TABLES, "训练域表")
            return True, core_ready and legacy_ready, training_ready
    except Exception as exc:
        print(f"❌ PostgreSQL 连接失败: {exc}")
        print("   请检查：")
        print("   1. PostgreSQL 服务是否运行")
        print("   2. backend/.env 中的数据库配置是否正确")
        print("   3. 目标数据库是否已创建")
        print()
        return False, False, False


def check_chroma_status():
    """检查 Chroma 路径和可选 collection 状态。"""
    print("【2】Chroma 向量数据库状态（可选）")
    print("-" * 60)

    try:
        import config
    except Exception as exc:
        print(f"⚠️  Chroma 未启用或依赖缺失: {exc}")
        print("   当前训练主链路不依赖 Chroma，可按需忽略。")
        print()
        return "not_enabled"

    db_path = os.path.abspath(config.VECTOR_DB_PATH)
    if not os.path.exists(db_path):
        print(f"⚠️  向量库目录不存在: {db_path}")
        print("   当前训练主链路不依赖 Chroma，可按需忽略。")
        print()
        return "missing_path"

    print(f"✅ 向量库目录存在: {db_path}")
    print("ℹ️  当前脚本不再主动实例化 Chroma 客户端，避免 optional 依赖的 telemetry 噪音干扰排障。")
    print("   如需初始化或校验 collection，请按需运行 `python scripts/init_chroma.py`。")
    print()
    return "path_ready"


def main() -> None:
    """执行数据库状态检查并输出总结。"""
    _enable_utf8_console()
    _bootstrap_backend_path()

    pg_connected, core_ready, training_ready = check_postgresql_status()
    chroma_ready = check_chroma_status()

    print("=" * 60)
    print("检测总结")
    print("=" * 60)
    if not pg_connected:
        print("❌ PostgreSQL 未就绪，当前系统无法正常运行。")
        return

    if core_ready and training_ready:
        print("✅ PostgreSQL 核心表与训练表都已就绪。")
    elif core_ready:
        print("⚠️  PostgreSQL 已连通，但训练域表不完整，建议先运行 `python scripts/init_db.py`。")
    else:
        print("⚠️  PostgreSQL 已连通，但核心业务表不完整，建议先运行 `python scripts/init_db.py`。")

    if chroma_ready == "path_ready":
        print("ℹ️  Chroma 目录已就绪，但当前脚本未校验 collection。")
    else:
        print("ℹ️  Chroma 当前未就绪或未启用；P1/P2 训练主链路可继续工作。")


if __name__ == "__main__":
    main()
