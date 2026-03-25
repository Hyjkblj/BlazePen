"""Unit tests for training media task policy contract."""

from __future__ import annotations

import unittest

from training.exceptions import TrainingMediaTaskInvalidError, TrainingMediaTaskUnsupportedError
from training.media_task_policy import TrainingMediaTaskPolicy


class TrainingMediaTaskPolicyTestCase(unittest.TestCase):
    def setUp(self):
        self.policy = TrainingMediaTaskPolicy()

    def test_should_build_deterministic_idempotency_key_for_equivalent_payloads(self):
        first = self.policy.normalize_create_request(
            session_id="session-1",
            round_no=2,
            task_type="image",
            payload={
                "prompt": "draw skyline",
                "style": {"color": "warm", "mood": "cinematic"},
                "size": [1024, 1024],
            },
            idempotency_key=None,
            max_retries=1,
        )
        second = self.policy.normalize_create_request(
            session_id="session-1",
            round_no=2,
            task_type="image",
            payload={
                "size": [1024, 1024],
                "style": {"mood": "cinematic", "color": "warm"},
                "prompt": "draw skyline",
            },
            idempotency_key=None,
            max_retries=1,
        )

        self.assertEqual(first.canonical_payload, second.canonical_payload)
        self.assertEqual(first.idempotency_key, second.idempotency_key)

    def test_should_keep_explicit_idempotency_key(self):
        normalized = self.policy.normalize_create_request(
            session_id="session-1",
            round_no=None,
            task_type="tts",
            payload={"text": "hello world"},
            idempotency_key="manual-key-1",
            max_retries=0,
        )

        self.assertEqual(normalized.idempotency_key, "manual-key-1")

    def test_should_reject_unsupported_task_type(self):
        with self.assertRaises(TrainingMediaTaskUnsupportedError):
            self.policy.normalize_create_request(
                session_id="session-1",
                round_no=1,
                task_type="video",
                payload={"prompt": "x"},
                idempotency_key=None,
                max_retries=0,
            )

    def test_should_reject_non_object_payload(self):
        with self.assertRaises(TrainingMediaTaskInvalidError):
            self.policy.normalize_create_request(
                session_id="session-1",
                round_no=1,
                task_type="text",
                payload=["not", "an", "object"],
                idempotency_key=None,
                max_retries=0,
            )

    def test_should_reject_non_finite_float_payload_values(self):
        with self.assertRaises(TrainingMediaTaskInvalidError):
            self.policy.normalize_create_request(
                session_id="session-1",
                round_no=1,
                task_type="text",
                payload={"temperature": float("inf")},
                idempotency_key=None,
                max_retries=0,
            )


if __name__ == "__main__":
    unittest.main()
