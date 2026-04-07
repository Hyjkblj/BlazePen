"""Unit tests for session storyline expansion policy."""

from __future__ import annotations

import unittest

from training.session_storyline_policy import SessionStorylinePolicy


class SessionStorylinePolicyTestCase(unittest.TestCase):
    def setUp(self):
        self.policy = SessionStorylinePolicy()
        self.base_sequence = [
            {"id": "S1", "title": "Scene 1"},
            {"id": "S2", "title": "Scene 2"},
            {"id": "S3", "title": "Scene 3"},
            {"id": "S4", "title": "Scene 4"},
            {"id": "S5", "title": "Scene 5"},
            {"id": "S6", "title": "Scene 6"},
        ]

    def test_should_expand_major_and_micro_scenes_for_guided_identity(self):
        result = self.policy.build_session_sequence(
            training_mode="guided",
            base_sequence=self.base_sequence,
            player_profile={"name": "Li", "identity": "战地记者"},
        )

        self.assertGreaterEqual(len(result), len(self.base_sequence) * 3)
        self.assertEqual(result[0]["id"], "S1")

        ids = [item["id"] for item in result]
        self.assertEqual(len(ids), len(set(ids)))

        for scene in result:
            self.assertTrue(str(scene.get("mission") or "").strip())
            self.assertTrue(str(scene.get("decision_focus") or "").strip())
            self.assertGreaterEqual(len(scene.get("options") or []), 3)
            self.assertIn(scene.get("scene_level"), {"major", "micro"})
            self.assertEqual(scene.get("is_assessment_round"), True)

        for major_id in [item["id"] for item in self.base_sequence]:
            major_items = [item for item in result if item.get("id") == major_id]
            self.assertEqual(len(major_items), 1)
            micro_items = [
                item
                for item in result
                if item.get("major_scene_id") == major_id and item.get("scene_level") == "micro"
            ]
            self.assertIn(len(micro_items), {2, 3})

        for index, scene in enumerate(result):
            expected_prev = result[index - 1]["id"] if index > 0 else None
            expected_next = result[index + 1]["id"] if index + 1 < len(result) else None
            self.assertEqual(scene.get("storyline_prev_scene_id"), expected_prev)
            self.assertEqual(scene.get("storyline_next_scene_id"), expected_next)
            self.assertEqual(scene.get("storyline_order"), index + 1)
            self.assertEqual(scene.get("storyline_total"), len(result))

    def test_should_keep_base_sequence_when_not_eligible(self):
        # guided mode without identity should still expand (structure != content)
        no_identity = self.policy.build_session_sequence(
            training_mode="guided",
            base_sequence=self.base_sequence,
            player_profile={"name": "Li"},
        )
        self.assertGreaterEqual(len(no_identity), len(self.base_sequence) * 3)

        # guided mode with no profile at all should also expand
        no_profile = self.policy.build_session_sequence(
            training_mode="guided",
            base_sequence=self.base_sequence,
            player_profile=None,
        )
        self.assertGreaterEqual(len(no_profile), len(self.base_sequence) * 3)

        # non-guided modes should not expand
        non_guided = self.policy.build_session_sequence(
            training_mode="self-paced",
            base_sequence=self.base_sequence,
            player_profile={"identity": "战地记者"},
        )
        self.assertEqual([item["id"] for item in non_guided], [item["id"] for item in self.base_sequence])

    def test_should_respect_explicit_expansion_overrides(self):
        # disable_storyline_expansion overrides guided mode
        disabled = self.policy.build_session_sequence(
            training_mode="guided",
            base_sequence=self.base_sequence,
            player_profile={"disable_storyline_expansion": True},
        )
        self.assertEqual([item["id"] for item in disabled], [item["id"] for item in self.base_sequence])

        # force_storyline_expansion overrides non-guided mode
        forced = self.policy.build_session_sequence(
            training_mode="self-paced",
            base_sequence=self.base_sequence,
            player_profile={"force_storyline_expansion": True},
        )
        self.assertGreaterEqual(len(forced), len(self.base_sequence) * 3)

    def test_should_generate_unique_storyline_per_session_without_explicit_seed(self):
        first = self.policy.build_session_sequence(
            training_mode="guided",
            base_sequence=self.base_sequence,
            player_profile={"identity": "战地记者"},
        )
        second = self.policy.build_session_sequence(
            training_mode="guided",
            base_sequence=self.base_sequence,
            player_profile={"identity": "战地记者"},
        )

        first_micro_ids = [item["id"] for item in first if item.get("scene_level") == "micro"]
        second_micro_ids = [item["id"] for item in second if item.get("scene_level") == "micro"]
        self.assertNotEqual(first_micro_ids, second_micro_ids)


if __name__ == "__main__":
    unittest.main()

