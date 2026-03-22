from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from database.db_manager import DatabaseManager


PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent


def run_release_db_script(script_relative_path: str) -> None:
    """Run the explicit release-chain DB script from the project root."""
    completed = subprocess.run(
        [sys.executable, "-X", "utf8", script_relative_path],
        cwd=PROJECT_ROOT_DIR,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"database bootstrap script failed: script={script_relative_path}, "
            f"exit_code={completed.returncode}"
        )


def run_init_db_script() -> None:
    """Run the explicit database initialization / migration script."""
    run_release_db_script("scripts/init_db.py")


def run_check_database_status_script() -> None:
    """Run the explicit database status check script."""
    run_release_db_script("scripts/check_database_status.py")


def bootstrap_database(*, skip_init_db: bool, check_db_status: bool) -> DatabaseManager:
    """Prepare the DB for local training runners via the explicit release chain."""
    if not skip_init_db:
        run_init_db_script()

    if check_db_status:
        run_check_database_status_script()

    db_manager = DatabaseManager()
    db_manager.check_connection()
    return db_manager
