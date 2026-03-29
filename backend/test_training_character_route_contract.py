"""Training character route contract tests for typed error mappings."""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.error_codes import CHARACTER_NOT_FOUND, TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT
from api.dependencies import (
    get_character_service,
    get_image_service,
    get_training_character_preview_job_service,
)
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import training_characters
from api.services.character_service import CharacterNotFoundError
from api.services.training_character_preview_job_service import (
    TrainingCharacterPreviewCharacterNotFoundError,
    TrainingCharacterPreviewJobConflictError,
    TrainingCharacterPreviewJobInvalidError,
)
from training.exceptions import TrainingStorageUnavailableError


class _FakeCharacterService:
    def create_character(self, request_data):
        return 42

    def get_character(self, character_id):
        if int(character_id) == 404:
            raise CharacterNotFoundError(character_id=404)
        return {
            "character_id": str(character_id),
            "name": "stub",
            "appearance": {},
            "personality": {},
            "background": {},
        }

    def get_character_images(self, character_id):
        return []


class _FakeImageService:
    def remove_background_with_rembg(self, image_path, character_id, rename_to_standard=False):
        return "D:/fake/path/image.png"

    def delete_unselected_character_images(self, character_id, image_urls, selected_index):
        return 0


class _FakePreviewJobRecord:
    def __init__(self, payload):
        self.payload = dict(payload)

    def to_dict(self):
        return dict(self.payload)


class _FakePreviewJobService:
    def create_preview_job(
        self,
        *,
        character_id,
        idempotency_key,
        user_id=None,
        image_type="portrait",
        group_count=3,
        generate_scene_groups=False,
        scene_group_count=6,
        micro_scene_min=2,
        micro_scene_max=3,
    ):
        if int(character_id) == 404:
            raise TrainingCharacterPreviewCharacterNotFoundError(character_id=404)
        if str(idempotency_key) == "invalid-preview-key":
            raise TrainingCharacterPreviewJobInvalidError("preview payload is invalid")
        if str(idempotency_key) == "conflict-preview-key":
            raise TrainingCharacterPreviewJobConflictError(
                idempotency_key=idempotency_key,
                existing_job_id="preview-job-existing",
            )
        if str(idempotency_key) == "storage-down-key":
            raise TrainingStorageUnavailableError(
                message="training preview storage unavailable: operation=create_preview_job",
                details={"operation": "create_preview_job"},
            )
        return _FakePreviewJobRecord(
            {
                "job_id": "preview-job-1",
                "character_id": int(character_id),
                "idempotency_key": idempotency_key,
                "status": "pending",
                "image_urls": [],
                "scene_storyline_script": {},
                "scene_groups": [],
                "scene_generation_status": "pending",
                "scene_generation_error": None,
                "scene_generated_at": None,
                "attempt_count": 0,
                "last_failed_at": None,
                "last_error_message": None,
                "error_message": None,
                "created_at": "2026-03-27T12:00:00",
                "updated_at": "2026-03-27T12:00:00",
            }
        )

    def get_preview_job(self, job_id):
        if str(job_id) == "storage-down-job":
            raise TrainingStorageUnavailableError(
                message="training preview storage unavailable: operation=get_preview_job",
                details={"operation": "get_preview_job"},
            )
        return _FakePreviewJobRecord(
            {
                "job_id": str(job_id),
                "character_id": 42,
                "idempotency_key": "preview-key-1",
                "status": "pending",
                "image_urls": [],
                "scene_storyline_script": {},
                "scene_groups": [],
                "scene_generation_status": "pending",
                "scene_generation_error": None,
                "scene_generated_at": None,
                "attempt_count": 0,
                "last_failed_at": None,
                "last_error_message": None,
                "error_message": None,
                "created_at": "2026-03-27T12:00:00",
                "updated_at": "2026-03-27T12:00:00",
            }
        )


class TrainingCharacterRouteContractTestCase(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        install_common_exception_handlers(self.app)
        self.app.include_router(training_characters.router, prefix="/api")
        self.app.dependency_overrides[get_character_service] = lambda: _FakeCharacterService()
        self.app.dependency_overrides[get_image_service] = lambda: _FakeImageService()
        self.app.dependency_overrides[get_training_character_preview_job_service] = (
            lambda: _FakePreviewJobService()
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_get_training_character_should_return_404_for_missing_character(self):
        response = self.client.get("/api/v1/training/characters/404")
        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], CHARACTER_NOT_FOUND)

    def test_get_training_character_should_return_typed_validation_error_for_invalid_id(self):
        response = self.client.get("/api/v1/training/characters/invalid")
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_get_training_identity_presets_should_return_typed_payload(self):
        response = self.client.get("/api/v1/training/characters/identity-presets")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["code"], 200)
        presets = payload.get("data", {}).get("presets", [])
        self.assertGreater(len(presets), 0)
        self.assertIn("code", presets[0])
        self.assertIn("default_name", presets[0])

    def test_create_preview_job_should_return_404_for_missing_character(self):
        response = self.client.post(
            "/api/v1/training/characters/preview-jobs",
            json={
                "character_id": 404,
                "idempotency_key": "preview-key-404",
            },
        )
        self.assertEqual(response.status_code, 404)

    def test_create_preview_job_should_map_typed_validation_error_to_400(self):
        response = self.client.post(
            "/api/v1/training/characters/preview-jobs",
            json={
                "character_id": 42,
                "idempotency_key": "invalid-preview-key",
            },
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_create_preview_job_should_map_conflict_to_409_with_typed_error(self):
        response = self.client.post(
            "/api/v1/training/characters/preview-jobs",
            json={
                "character_id": 42,
                "idempotency_key": "conflict-preview-key",
            },
        )
        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT)
        details = payload["error"].get("details", {})
        self.assertEqual(details.get("existing_job_id"), "preview-job-existing")

    def test_create_preview_job_should_expose_attempt_observability_fields(self):
        response = self.client.post(
            "/api/v1/training/characters/preview-jobs",
            json={
                "character_id": 42,
                "idempotency_key": "preview-key-observability",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        data = payload["data"]
        self.assertEqual(data.get("attempt_count"), 0)
        self.assertIsNone(data.get("last_failed_at"))
        self.assertIsNone(data.get("last_error_message"))

    def test_create_preview_job_should_map_storage_unavailable_to_503(self):
        response = self.client.post(
            "/api/v1/training/characters/preview-jobs",
            json={
                "character_id": 42,
                "idempotency_key": "storage-down-key",
            },
        )
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "TRAINING_STORAGE_UNAVAILABLE")

    def test_create_preview_job_should_reject_generate_scene_groups_when_runtime_disabled(self):
        response = self.client.post(
            "/api/v1/training/characters/preview-jobs",
            json={
                "character_id": 42,
                "idempotency_key": "preview-key-scene-disabled",
                "generate_scene_groups": True,
            },
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")
        self.assertEqual(
            payload["error"]["details"].get("field"),
            "generate_scene_groups",
        )
        self.assertEqual(
            payload["error"]["details"].get("reason"),
            "disabled_in_training_runtime",
        )

    def test_get_preview_job_should_map_storage_unavailable_to_503(self):
        response = self.client.get("/api/v1/training/characters/preview-jobs/storage-down-job")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "TRAINING_STORAGE_UNAVAILABLE")

    def test_get_training_character_images_should_return_typed_validation_error_for_invalid_id(self):
        response = self.client.get("/api/v1/training/characters/invalid/images")
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_remove_background_should_not_expose_local_path(self):
        response = self.client.post(
            "/api/v1/training/characters/42/remove-background",
            json={
                "image_url": "/static/images/characters/preview_42_1.png",
                "image_urls": ["/static/images/characters/preview_42_1.png"],
                "selected_index": 0,
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        data = payload.get("data", {})
        self.assertIn("selected_image_url", data)
        self.assertIn("transparent_url", data)
        self.assertIn("deleted_count", data)
        self.assertNotIn("local_path", data)

    def test_remove_background_should_return_typed_validation_error_for_invalid_id(self):
        response = self.client.post(
            "/api/v1/training/characters/invalid/remove-background",
            json={"image_url": "/static/images/characters/preview_42_1.png"},
        )
        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_ERROR")

    def test_openapi_should_expose_preview_job_attempt_observability_fields(self):
        openapi = self.app.openapi()
        components = openapi.get("components", {}).get("schemas", {})
        preview_schema = components.get("TrainingCharacterPreviewJobResponse", {})
        preview_properties = preview_schema.get("properties", {})
        self.assertIn("attempt_count", preview_properties)
        self.assertIn("last_failed_at", preview_properties)
        self.assertIn("last_error_message", preview_properties)

        envelope_schema = components.get("TrainingCharacterPreviewJobApiResponse", {})
        envelope_properties = envelope_schema.get("properties", {})
        self.assertIn("data", envelope_properties)

        post_200 = (
            openapi.get("paths", {})
            .get("/api/v1/training/characters/preview-jobs", {})
            .get("post", {})
            .get("responses", {})
            .get("200", {})
        )
        post_content = post_200.get("content", {}).get("application/json", {}).get("schema", {})
        self.assertIn("$ref", post_content)

    def test_openapi_should_expose_typed_training_character_route_envelopes(self):
        openapi = self.app.openapi()
        components = openapi.get("components", {}).get("schemas", {})
        self.assertIn("TrainingCharacterApiResponse", components)
        self.assertIn("TrainingCharacterImagesApiResponse", components)
        self.assertIn("TrainingCharacterRemoveBackgroundApiResponse", components)
        self.assertIn("TrainingIdentityPresetListApiResponse", components)

        create_200 = (
            openapi.get("paths", {})
            .get("/api/v1/training/characters/create", {})
            .get("post", {})
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        get_200 = (
            openapi.get("paths", {})
            .get("/api/v1/training/characters/{character_id}", {})
            .get("get", {})
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        images_200 = (
            openapi.get("paths", {})
            .get("/api/v1/training/characters/{character_id}/images", {})
            .get("get", {})
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        remove_bg_200 = (
            openapi.get("paths", {})
            .get("/api/v1/training/characters/{character_id}/remove-background", {})
            .get("post", {})
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )

        self.assertIn("$ref", create_200)
        self.assertIn("$ref", get_200)
        self.assertIn("$ref", images_200)
        self.assertIn("$ref", remove_bg_200)

    def test_openapi_should_expose_training_identity_preset_route_schema(self):
        openapi = self.app.openapi()
        get_200 = (
            openapi.get("paths", {})
            .get("/api/v1/training/characters/identity-presets", {})
            .get("get", {})
            .get("responses", {})
            .get("200", {})
            .get("content", {})
            .get("application/json", {})
            .get("schema", {})
        )
        self.assertIn("$ref", get_200)


if __name__ == "__main__":
    unittest.main()
