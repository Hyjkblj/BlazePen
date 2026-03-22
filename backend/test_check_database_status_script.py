from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import scripts.check_database_status as status_script


class CheckDatabaseStatusScriptTestCase(unittest.TestCase):
    def _run_main(self, *, pg_status: tuple[bool, bool, bool], chroma_status: str) -> str:
        captured_stdout = io.StringIO()

        with patch.object(status_script, "_enable_utf8_console"):
            with patch.object(status_script, "_bootstrap_backend_path"):
                with patch.object(status_script, "check_postgresql_status", return_value=pg_status):
                    with patch.object(status_script, "check_chroma_status", return_value=chroma_status):
                        with patch("sys.stdout", new=captured_stdout):
                            status_script.main()

        return captured_stdout.getvalue()

    def test_main_should_report_postgresql_not_ready(self):
        output = self._run_main(
            pg_status=(False, False, False),
            chroma_status="not_enabled",
        )

        self.assertIn("检测总结", output)
        self.assertIn("PostgreSQL 未就绪", output)

    def test_main_should_report_core_and_training_tables_ready(self):
        output = self._run_main(
            pg_status=(True, True, True),
            chroma_status="path_ready",
        )

        self.assertIn("PostgreSQL 核心表与训练表都已就绪", output)
        self.assertIn("Chroma 目录已就绪", output)

    def test_main_should_report_training_tables_incomplete(self):
        output = self._run_main(
            pg_status=(True, True, False),
            chroma_status="not_enabled",
        )

        self.assertIn("训练域表不完整", output)
        self.assertIn("P1/P2 训练主链路可继续工作", output)


if __name__ == "__main__":
    unittest.main()
