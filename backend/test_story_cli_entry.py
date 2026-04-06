from __future__ import annotations

import io
import unittest
from unittest.mock import patch

import run_story_cli


class StoryCliEntryTestCase(unittest.TestCase):
    def test_main_should_dispatch_init_db_command(self):
        with patch.object(run_story_cli, "run_init_db_script") as init_db_mock:
            exit_code = run_story_cli.main(["init-db"])

        self.assertEqual(exit_code, 0)
        init_db_mock.assert_called_once_with()

    def test_main_should_dispatch_check_db_command(self):
        with patch.object(run_story_cli, "run_check_database_status_script") as check_db_mock:
            exit_code = run_story_cli.main(["check-db"])

        self.assertEqual(exit_code, 0)
        check_db_mock.assert_called_once_with()

    def test_main_should_run_default_story_smoke_suite(self):
        with patch.object(run_story_cli, "run_story_smoke_suite", return_value=7) as smoke_runner:
            exit_code = run_story_cli.main(["smoke"])

        self.assertEqual(exit_code, 7)
        smoke_runner.assert_called_once_with(list(run_story_cli.DEFAULT_STORY_SMOKE_TEST_ARGS))

    def test_main_should_forward_custom_smoke_args_after_double_dash(self):
        with patch.object(run_story_cli, "run_story_smoke_suite", return_value=9) as smoke_runner:
            exit_code = run_story_cli.main(
                [
                    "smoke",
                    "--",
                    "backend/test_story_route_smoke.py",
                    "-q",
                ]
            )

        self.assertEqual(exit_code, 9)
        smoke_runner.assert_called_once_with(
            [
                "backend/test_story_route_smoke.py",
                "-q",
            ]
        )

    def test_main_should_dispatch_probe_llm_command(self):
        with patch.object(run_story_cli, "run_story_llm_probe", return_value=3) as llm_probe_runner:
            exit_code = run_story_cli.main(
                [
                    "probe-llm",
                    "--character-id",
                    "7",
                    "--scene-id",
                    "school",
                ]
            )

        self.assertEqual(exit_code, 3)
        llm_probe_runner.assert_called_once_with(
            [
                "--character-id",
                "7",
                "--scene-id",
                "school",
            ]
        )

    def test_main_should_show_root_help_when_requested(self):
        captured_stdout = io.StringIO()

        with patch("sys.stdout", new=captured_stdout):
            exit_code = run_story_cli.main(["--help"])

        self.assertEqual(exit_code, 0)
        help_output = captured_stdout.getvalue()
        self.assertIn("Story backend unified CLI entrypoint", help_output)
        self.assertIn("smoke", help_output)
        self.assertIn("probe-llm", help_output)


if __name__ == "__main__":
    unittest.main()
