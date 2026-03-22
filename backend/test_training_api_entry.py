from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import run_training_api


class TrainingApiEntryTestCase(unittest.TestCase):
    def test_training_entry_main_should_use_training_env_variables(self):
        expected_workdir = os.path.dirname(os.path.abspath(run_training_api.__file__))

        with patch.dict(
            os.environ,
            {
                "TRAINING_API_HOST": "127.0.0.1",
                "TRAINING_API_PORT": "8110",
                "TRAINING_API_RELOAD": "false",
            },
            clear=False,
        ):
            with patch.object(run_training_api.os, "chdir") as chdir_mock:
                with patch.object(run_training_api.os, "getcwd", return_value=expected_workdir):
                    with patch.object(run_training_api.uvicorn, "run") as uvicorn_run_mock:
                        with patch("builtins.print") as print_mock:
                            run_training_api.main()

        chdir_mock.assert_called_once_with(expected_workdir)
        uvicorn_run_mock.assert_called_once_with(
            "api.training_app:app",
            host="127.0.0.1",
            port=8110,
            reload=False,
        )
        print_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
