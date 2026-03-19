from __future__ import annotations

import unittest

from story.story_asset_service import StoryAssetService


class StoryAssetServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.service = StoryAssetService()

    def test_build_story_assets_should_mark_ready_pending_and_failed(self):
        assets = self.service.build_story_assets(
            scene_image_url="/static/images/scenes/scene.png",
            composite_image_url=None,
            composite_pending=True,
        )

        self.assertEqual(assets["scene_image"]["status"], "ready")
        self.assertEqual(assets["scene_image"]["url"], "/static/images/scenes/scene.png")
        self.assertEqual(assets["composite_image"]["status"], "pending")
        self.assertEqual(assets["composite_image"]["detail"], "generation_pending")

    def test_merge_story_assets_should_backfill_from_legacy_urls(self):
        payload = self.service.merge_story_assets(
            {
                "scene_image_url": "/static/images/scenes/scene.png",
                "composite_image_url": None,
            }
        )

        self.assertEqual(payload["assets"]["scene_image"]["status"], "ready")
        self.assertEqual(payload["assets"]["scene_image"]["url"], "/static/images/scenes/scene.png")
        self.assertEqual(payload["assets"]["composite_image"]["status"], "failed")
        self.assertEqual(payload["assets"]["composite_image"]["detail"], "not_available")

    def test_merge_story_assets_should_preserve_existing_structured_status(self):
        payload = self.service.merge_story_assets(
            {
                "scene_image_url": "/static/images/scenes/scene.png",
                "assets": {
                    "scene_image": {
                        "type": "scene_image",
                        "status": "pending",
                        "url": None,
                        "detail": "generation_pending",
                    }
                },
            }
        )

        self.assertEqual(payload["assets"]["scene_image"]["status"], "pending")
        self.assertIsNone(payload["assets"]["scene_image"]["url"])
        self.assertEqual(payload["assets"]["composite_image"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
