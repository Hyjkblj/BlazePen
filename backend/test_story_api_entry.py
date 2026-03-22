from __future__ import annotations

import os
import unittest
from unittest.mock import patch

import run_api
import run_story_api


class StoryApiEntryTestCase(unittest.TestCase):
    def test_story_entry_main_should_use_story_env_variables(self):
        expected_workdir = os.path.dirname(os.path.abspath(run_story_api.__file__))

        with patch.dict(
            os.environ,
            {
                "STORY_API_HOST": "127.0.0.1",
                "STORY_API_PORT": "8100",
                "STORY_API_RELOAD": "false",
            },
            clear=False,
        ):
            with patch.object(run_story_api.os, "chdir") as chdir_mock:
                with patch.object(run_story_api.os, "getcwd", return_value=expected_workdir):
                    with patch.object(run_story_api.uvicorn, "run") as uvicorn_run_mock:
                        with patch("builtins.print") as print_mock:
                            run_story_api.main()

        chdir_mock.assert_called_once_with(expected_workdir)
        uvicorn_run_mock.assert_called_once_with(
            "api.app:app",
            host="127.0.0.1",
            port=8100,
            reload=False,
        )
        print_mock.assert_called_once()

    def test_legacy_run_api_should_delegate_to_story_entrypoint(self):
        with patch.object(run_api.run_story_api, "main") as story_main_mock:
            run_api.main()

        story_main_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
