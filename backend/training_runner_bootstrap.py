from __future__ import annotations

from backend_runner_bootstrap import run_release_db_script
from database.db_manager import DatabaseManager


def run_init_db_script() -> None:
    """Compatibility wrapper for legacy imports."""
    run_release_db_script("scripts/init_db.py")


def run_check_database_status_script() -> None:
    """Compatibility wrapper for legacy imports."""
    run_release_db_script("scripts/check_database_status.py")


def bootstrap_database(*, skip_init_db: bool, check_db_status: bool) -> DatabaseManager:
    """Compatibility wrapper that keeps legacy import paths operational.

    Transitional compatibility:
    - Preferred module: backend_runner_bootstrap.py
    - Legacy module: training_runner_bootstrap.py
    """
    if not skip_init_db:
        run_init_db_script()

    if check_db_status:
        run_check_database_status_script()

    db_manager = DatabaseManager()
    db_manager.check_connection()
    return db_manager
