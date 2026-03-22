from __future__ import annotations

import argparse
import unittest
from unittest.mock import MagicMock, patch

import backend_runner_bootstrap
import run_training_service_cli as cli_runner
import run_training_service_local as local_runner
import training_runner_bootstrap


class BackendRunnerBootstrapTestCase(unittest.TestCase):
    def test_bootstrap_database_should_run_explicit_scripts_before_connection_check(self):
        fake_db_manager = MagicMock()

        with patch.object(backend_runner_bootstrap, "run_init_db_script") as init_db_mock:
            with patch.object(
                backend_runner_bootstrap,
                "run_check_database_status_script",
            ) as check_db_mock:
                with patch.object(
                    backend_runner_bootstrap,
                    "DatabaseManager",
                    return_value=fake_db_manager,
                ):
                    result = backend_runner_bootstrap.bootstrap_database(
                        skip_init_db=False,
                        check_db_status=True,
                    )

        self.assertIs(result, fake_db_manager)
        init_db_mock.assert_called_once_with()
        check_db_mock.assert_called_once_with()
        fake_db_manager.check_connection.assert_called_once_with()

    def test_bootstrap_database_should_skip_scripts_but_still_check_connection(self):
        fake_db_manager = MagicMock()

        with patch.object(backend_runner_bootstrap, "run_init_db_script") as init_db_mock:
            with patch.object(
                backend_runner_bootstrap,
                "run_check_database_status_script",
            ) as check_db_mock:
                with patch.object(
                    backend_runner_bootstrap,
                    "DatabaseManager",
                    return_value=fake_db_manager,
                ):
                    result = backend_runner_bootstrap.bootstrap_database(
                        skip_init_db=True,
                        check_db_status=False,
                    )

        self.assertIs(result, fake_db_manager)
        init_db_mock.assert_not_called()
        check_db_mock.assert_not_called()
        fake_db_manager.check_connection.assert_called_once_with()


class TrainingRunnerBootstrapCompatibilityTestCase(unittest.TestCase):
    def test_legacy_bootstrap_should_remain_compatible_for_existing_importers(self):
        fake_db_manager = MagicMock()

        with patch.object(training_runner_bootstrap, "run_init_db_script") as init_db_mock:
            with patch.object(
                training_runner_bootstrap,
                "run_check_database_status_script",
            ) as check_db_mock:
                with patch.object(
                    training_runner_bootstrap,
                    "DatabaseManager",
                    return_value=fake_db_manager,
                ):
                    result = training_runner_bootstrap.bootstrap_database(
                        skip_init_db=False,
                        check_db_status=True,
                    )

        self.assertIs(result, fake_db_manager)
        init_db_mock.assert_called_once_with()
        check_db_mock.assert_called_once_with()
        fake_db_manager.check_connection.assert_called_once_with()


class TrainingRunnerWiringTestCase(unittest.TestCase):
    def test_local_smoke_should_use_shared_bootstrap(self):
        args = argparse.Namespace(
            user_id="local-runner-user",
            training_mode="self-paced",
            name="Lin Min",
            gender="female",
            identity="field-reporter",
            age=24,
            round_limit=1,
            selection_strategy="recommended",
            skip_init_db=False,
            check_db_status=True,
            save_json_dir="",
        )
        fake_service = MagicMock()
        fake_service.init_training.return_value = {
            "session_id": "session-local",
            "player_profile": {"name": "Lin Min"},
            "next_scenario": {"id": "S1", "title": "Intro", "options": [{"id": "A"}]},
            "scenario_candidates": [],
        }
        fake_service.submit_round.return_value = {
            "session_id": "session-local",
            "round_no": 1,
            "is_completed": True,
            "evaluation": {"risk_flags": []},
            "k_state": {},
            "s_state": {},
        }
        fake_service.get_progress.return_value = {"session_id": "session-local", "round_no": 1}
        fake_service.get_report.return_value = {
            "session_id": "session-local",
            "ending": {"ending_type": "steady"},
            "summary": {"score": 0.8},
            "improvement": {},
        }
        fake_service.get_diagnostics.return_value = {
            "session_id": "session-local",
            "summary": {"alerts": 0},
        }

        with patch.object(local_runner, "_configure_stdout_encoding"):
            with patch.object(local_runner, "bootstrap_database", return_value=MagicMock()) as bootstrap_mock:
                with patch.object(local_runner, "TrainingService", return_value=fake_service):
                    exit_code = local_runner.run_local_smoke(args)

        self.assertEqual(exit_code, 0)
        bootstrap_mock.assert_called_once_with(skip_init_db=False, check_db_status=True)

    def test_interactive_cli_should_use_shared_bootstrap(self):
        args = argparse.Namespace(
            user_id="cli-runner-user",
            training_mode="self-paced",
            name="Lin Min",
            gender="female",
            identity="field-reporter",
            age=24,
            skip_init_db=False,
            check_db_status=True,
            save_json_dir="",
            plain_mode=True,
        )
        fake_service = MagicMock()
        fake_service.init_training.return_value = {
            "session_id": "session-cli",
            "next_scenario": {"id": "S1", "title": "Intro"},
            "scenario_candidates": [],
        }
        fake_service.submit_round.return_value = {
            "session_id": "session-cli",
            "round_no": 1,
            "is_completed": True,
        }
        fake_service.get_progress.return_value = {
            "session_id": "session-cli",
            "round_no": 1,
            "status": "completed",
        }
        fake_service.get_report.return_value = {
            "session_id": "session-cli",
            "ending": {"ending_type": "steady"},
            "summary": {"score": 0.8},
            "improvement": {},
        }
        fake_service.get_diagnostics.return_value = {
            "session_id": "session-cli",
            "summary": {"alerts": 0},
        }

        with patch.object(cli_runner, "_configure_stdout_encoding"):
            with patch.object(cli_runner, "bootstrap_database", return_value=MagicMock()) as bootstrap_mock:
                with patch.object(cli_runner, "TrainingService", return_value=fake_service):
                    with patch.object(
                        cli_runner,
                        "_pick_scenario_from_bundle",
                        return_value={"id": "S1", "title": "Intro"},
                    ):
                        with patch.object(cli_runner, "_pick_option_and_text", return_value=("A", "answer")):
                            exit_code = cli_runner.run_interactive_cli(args)

        self.assertEqual(exit_code, 0)
        bootstrap_mock.assert_called_once_with(skip_init_db=False, check_db_status=True)


if __name__ == "__main__":
    unittest.main()
