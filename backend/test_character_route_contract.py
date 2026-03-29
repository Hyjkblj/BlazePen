"""Character route contract regression tests."""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.dependencies import get_character_service
from api.middleware.error_handler import install_common_exception_handlers
from api.routers import characters


class _FakeCharacterService:
    def create_character(self, request_data):
        return 1

    def generate_character_image(self, *args, **kwargs):
        return []

    def get_character(self, character_id):
        return {"character_id": str(character_id), "name": "stub"}

    def get_character_images(self, character_id):
        return []


class CharacterRouteContractTestCase(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        install_common_exception_handlers(self.app)
        self.app.include_router(characters.router, prefix="/api")
        self.app.dependency_overrides[get_character_service] = lambda: _FakeCharacterService()
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.dependency_overrides.clear()

    def test_create_character_should_reject_empty_payload(self):
        response = self.client.post("/api/v1/characters/create", json={})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
