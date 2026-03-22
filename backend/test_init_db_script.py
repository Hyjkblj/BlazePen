"""Tests for the explicit DB migration bootstrap script."""

from __future__ import annotations

import io
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import scripts.init_db as init_db_script


class InitDbScriptTestCase(unittest.TestCase):
    def test_migrate_database_should_stamp_legacy_database_before_upgrade(self):
        fake_engine = MagicMock()
        fake_config = object()

        with patch.object(init_db_script, "create_engine", return_value=fake_engine):
            with patch.object(init_db_script, "_build_alembic_config", return_value=fake_config):
                with patch.object(init_db_script, "_has_table", return_value=False):
                    with patch.object(init_db_script, "_has_managed_tables", return_value=True):
                        with patch.object(init_db_script.command, "stamp") as stamp_mock:
                            with patch.object(init_db_script.command, "upgrade") as upgrade_mock:
                                init_db_script.migrate_database(
                                    database_url="postgresql://test",
                                    backend_dir=Path("backend"),
                                )

        stamp_mock.assert_called_once_with(fake_config, init_db_script.BASELINE_REVISION)
        upgrade_mock.assert_called_once_with(fake_config, "head")
        fake_engine.dispose.assert_called_once_with()

    def test_migrate_database_should_upgrade_clean_database_without_stamp(self):
        fake_engine = MagicMock()
        fake_config = object()

        with patch.object(init_db_script, "create_engine", return_value=fake_engine):
            with patch.object(init_db_script, "_build_alembic_config", return_value=fake_config):
                with patch.object(init_db_script, "_has_table", return_value=True):
                    with patch.object(init_db_script, "_has_managed_tables", return_value=True):
                        with patch.object(init_db_script.command, "stamp") as stamp_mock:
                            with patch.object(init_db_script.command, "upgrade") as upgrade_mock:
                                init_db_script.migrate_database(
                                    database_url="postgresql://test",
                                    backend_dir=Path("backend"),
                                )

        stamp_mock.assert_not_called()
        upgrade_mock.assert_called_once_with(fake_config, "head")
        fake_engine.dispose.assert_called_once_with()

    def test_ensure_database_exists_should_create_missing_database_once(self):
        fake_connection = MagicMock()
        fake_connection.execute.side_effect = [
            SimpleNamespace(scalar=lambda: None),
            None,
        ]
        fake_connect_context = MagicMock()
        fake_connect_context.__enter__.return_value = fake_connection
        fake_connect_context.__exit__.return_value = False
        fake_engine = MagicMock()
        fake_engine.connect.return_value = fake_connect_context

        config_module = SimpleNamespace(
            DB_CONFIG={
                "user": "tester",
                "password": "secret",
                "host": "localhost",
                "port": 5432,
                "database": "blazepen_test",
            }
        )

        with patch.object(init_db_script, "create_engine", return_value=fake_engine):
            database_name, created = init_db_script.ensure_database_exists(config_module)

        self.assertEqual(database_name, "blazepen_test")
        self.assertTrue(created)
        self.assertEqual(fake_connection.execute.call_count, 2)
        fake_engine.dispose.assert_called_once_with()

    def test_create_database_should_run_migration_and_print_table_summary(self):
        backend_dir = Path("backend")
        config_module = SimpleNamespace(
            DB_CONFIG={
                "user": "tester",
                "password": "secret",
                "host": "localhost",
                "port": 5432,
                "database": "blazepen_test",
            }
        )
        fake_engine = MagicMock()
        fake_inspector = MagicMock()
        fake_inspector.get_table_names.return_value = [
            "alembic_version",
            "training_sessions",
            "training_rounds",
        ]
        captured_stdout = io.StringIO()

        with patch.object(init_db_script, "_enable_utf8_console"):
            with patch.object(init_db_script, "_bootstrap_backend_path", return_value=backend_dir):
                with patch.dict(sys.modules, {"config": config_module}):
                    with patch.object(
                        init_db_script,
                        "ensure_database_exists",
                        return_value=("blazepen_test", True),
                    ):
                        with patch.object(init_db_script, "migrate_database") as migrate_mock:
                            with patch.object(init_db_script, "create_engine", return_value=fake_engine):
                                with patch.object(init_db_script, "inspect", return_value=fake_inspector):
                                    with patch("sys.stdout", new=captured_stdout):
                                        init_db_script.create_database()

        migrate_mock.assert_called_once_with(
            database_url="postgresql://tester:secret@localhost:5432/blazepen_test",
            backend_dir=backend_dir,
        )
        fake_engine.dispose.assert_called_once_with()
        self.assertIn("training_sessions", captured_stdout.getvalue())
        self.assertIn("PostgreSQL", captured_stdout.getvalue())

    def test_create_database_should_exit_with_status_1_when_migration_fails(self):
        backend_dir = Path("backend")
        config_module = SimpleNamespace(
            DB_CONFIG={
                "user": "tester",
                "password": "secret",
                "host": "localhost",
                "port": 5432,
                "database": "blazepen_test",
            }
        )
        captured_stdout = io.StringIO()

        with patch.object(init_db_script, "_enable_utf8_console"):
            with patch.object(init_db_script, "_bootstrap_backend_path", return_value=backend_dir):
                with patch.dict(sys.modules, {"config": config_module}):
                    with patch.object(
                        init_db_script,
                        "ensure_database_exists",
                        return_value=("blazepen_test", False),
                    ):
                        with patch.object(
                            init_db_script,
                            "migrate_database",
                            side_effect=RuntimeError("migration failed"),
                        ):
                            with patch("traceback.print_exc"):
                                with patch("sys.stdout", new=captured_stdout):
                                    with self.assertRaises(SystemExit) as cm:
                                        init_db_script.create_database()

        self.assertEqual(cm.exception.code, 1)
        self.assertIn("数据库初始化失败", captured_stdout.getvalue())
        self.assertIn("migration failed", captured_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
