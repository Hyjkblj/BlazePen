from __future__ import annotations

import io
import unittest
from pathlib import Path
from unittest.mock import patch

import run_training_cli


class TrainingCliEntryTestCase(unittest.TestCase):
    def test_main_should_dispatch_init_db_command(self):
        with patch.object(run_training_cli, "run_init_db_script") as init_db_mock:
            exit_code = run_training_cli.main(["init-db"])

        self.assertEqual(exit_code, 0)
        init_db_mock.assert_called_once_with()

    def test_main_should_dispatch_check_db_command(self):
        with patch.object(run_training_cli, "run_check_database_status_script") as check_db_mock:
            exit_code = run_training_cli.main(["check-db"])

        self.assertEqual(exit_code, 0)
        check_db_mock.assert_called_once_with()

    def test_main_should_dispatch_smoke_command_with_passthrough_args(self):
        with patch.object(run_training_cli.run_training_service_local, "main", return_value=7) as smoke_main:
            exit_code = run_training_cli.main(["smoke", "--check-db-status", "--round-limit", "1"])

        self.assertEqual(exit_code, 7)
        smoke_main.assert_called_once_with(["--check-db-status", "--round-limit", "1"])

    def test_main_should_dispatch_play_command_with_passthrough_args(self):
        with patch.object(run_training_cli.run_training_service_cli, "main", return_value=9) as play_main:
            exit_code = run_training_cli.main(["play", "--plain-mode"])

        self.assertEqual(exit_code, 9)
        play_main.assert_called_once_with(["--plain-mode"])

    def test_main_should_dispatch_experience_command_with_default_status_check_and_artifact_dir(self):
        fake_artifact_dir = Path("tmp/training-experience/test-run")

        with patch.object(
            run_training_cli,
            "_build_default_experience_artifact_dir",
            return_value=fake_artifact_dir,
        ):
            with patch.object(run_training_cli.run_training_service_local, "main", return_value=11) as smoke_main:
                exit_code = run_training_cli.main(["experience", "--round-limit", "3"])

        self.assertEqual(exit_code, 11)
        smoke_main.assert_called_once_with(
            [
                "--round-limit",
                "3",
                "--check-db-status",
                "--save-json-dir",
                str(fake_artifact_dir),
            ]
        )

    def test_main_should_dispatch_experience_command_without_overriding_explicit_args(self):
        with patch.object(run_training_cli.run_training_service_local, "main", return_value=12) as smoke_main:
            exit_code = run_training_cli.main(
                [
                    "experience",
                    "--skip-init-db",
                    "--check-db-status",
                    "--save-json-dir",
                    "custom-artifacts",
                ]
            )

        self.assertEqual(exit_code, 12)
        smoke_main.assert_called_once_with(
            [
                "--skip-init-db",
                "--check-db-status",
                "--save-json-dir",
                "custom-artifacts",
            ]
        )

    def test_main_should_dispatch_interactive_experience_command_to_play_runner(self):
        fake_artifact_dir = Path("tmp/training-experience/interactive-run")

        with patch.object(
            run_training_cli,
            "_build_default_experience_artifact_dir",
            return_value=fake_artifact_dir,
        ):
            with patch.object(run_training_cli.run_training_service_cli, "main", return_value=13) as play_main:
                with patch.object(run_training_cli.run_training_service_local, "main") as smoke_main:
                    exit_code = run_training_cli.main(
                        [
                            "experience",
                            "--interactive",
                            "--training-mode",
                            "guided",
                        ]
                    )

        self.assertEqual(exit_code, 13)
        smoke_main.assert_not_called()
        play_main.assert_called_once_with(
            [
                "--training-mode",
                "guided",
                "--check-db-status",
                "--save-json-dir",
                str(fake_artifact_dir),
            ]
        )

    def test_main_should_show_root_help_when_requested(self):
        captured_stdout = io.StringIO()

        with patch("sys.stdout", new=captured_stdout):
            exit_code = run_training_cli.main(["--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("训练后端统一 CLI 入口", captured_stdout.getvalue())
        self.assertIn("smoke", captured_stdout.getvalue())

    def test_main_should_show_smoke_help_via_underlying_runner(self):
        with patch.object(run_training_cli.run_training_service_local, "main", return_value=0) as smoke_main:
            exit_code = run_training_cli.main(["smoke", "--help"])

        self.assertEqual(exit_code, 0)
        smoke_main.assert_called_once_with(["--help"])

    def test_main_should_show_play_help_via_underlying_runner(self):
        with patch.object(run_training_cli.run_training_service_cli, "main", return_value=0) as play_main:
            exit_code = run_training_cli.main(["play", "--help"])

        self.assertEqual(exit_code, 0)
        play_main.assert_called_once_with(["--help"])

    def test_main_should_show_experience_help(self):
        captured_stdout = io.StringIO()

        with patch("sys.stdout", new=captured_stdout):
            exit_code = run_training_cli.main(["experience", "--help"])

        self.assertEqual(exit_code, 0)
        self.assertIn("One-click full backend training experience", captured_stdout.getvalue())
        self.assertIn("timestamped directory", captured_stdout.getvalue())
        self.assertIn("--interactive", captured_stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
