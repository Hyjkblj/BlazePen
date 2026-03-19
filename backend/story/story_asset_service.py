"""Story-domain asset orchestration and contract helpers."""

from __future__ import annotations

from concurrent.futures import Executor
import glob
import os
import re
from typing import Any, Dict
from urllib.parse import quote, unquote

from utils.logger import get_logger

logger = get_logger(__name__)


class StoryAssetService:
    """Build and resolve story asset payloads.

    Transitional scope for PR-BE-04:
    1. keep one stable story asset contract
    2. resolve media URLs in one place instead of route/service ad hoc logic
    3. push heavyweight generation work off the synchronous story path
    """

    READY = "ready"
    PENDING = "pending"
    FAILED = "failed"

    def __init__(self, image_service=None):
        self.image_service = image_service

    def build_story_assets(
        self,
        *,
        scene_image_url: str | None = None,
        composite_image_url: str | None = None,
        scene_pending: bool = False,
        composite_pending: bool = False,
    ) -> Dict[str, Dict[str, Any]]:
        return {
            "scene_image": self._build_asset_resource(
                asset_type="scene_image",
                url=scene_image_url,
                pending=scene_pending,
            ),
            "composite_image": self._build_asset_resource(
                asset_type="composite_image",
                url=composite_image_url,
                pending=composite_pending,
            ),
        }

    def merge_story_assets(
        self,
        payload: Dict[str, Any] | None,
        *,
        scene_pending: bool = False,
        composite_pending: bool = False,
    ) -> Dict[str, Any]:
        normalized = dict(payload or {})
        assets_payload = dict(normalized.get("assets") or {})

        normalized["assets"] = {
            "scene_image": self._normalize_asset_resource(
                asset_type="scene_image",
                payload=assets_payload.get("scene_image"),
                fallback_url=normalized.get("scene_image_url"),
                fallback_pending=scene_pending,
            ),
            "composite_image": self._normalize_asset_resource(
                asset_type="composite_image",
                payload=assets_payload.get("composite_image"),
                fallback_url=normalized.get("composite_image_url"),
                fallback_pending=composite_pending,
            ),
        }
        return normalized

    def resolve_scene_image_url(self, scene_id: str | None) -> str | None:
        """Resolve the current scene image into a stable static URL."""

        if not scene_id or self.image_service is None:
            return None

        try:
            scene_image_path = self.image_service.get_latest_scene_image_path(scene_id)
            if scene_image_path and os.path.exists(scene_image_path):
                return self._scene_path_to_url(scene_image_path)
        except Exception as exc:
            logger.warning(
                "failed to resolve scene image from latest path: scene_id=%s error=%s",
                scene_id,
                str(exc),
                exc_info=True,
            )

        try:
            return self._lookup_fallback_scene_image_url(scene_id)
        except Exception as exc:
            logger.warning(
                "failed to resolve fallback scene image: scene_id=%s error=%s",
                scene_id,
                str(exc),
                exc_info=True,
            )
            return None

    def find_latest_composite_image_url(
        self,
        *,
        character_id: int,
        scene_id: str | None,
    ) -> str | None:
        """Resolve the newest composite image for `(character, scene)` if it exists."""

        if not scene_id:
            return None

        composite_dir = self._resolve_dir("COMPOSITE_IMAGE_SAVE_DIR")
        if not composite_dir or not os.path.exists(composite_dir):
            return None

        character_id_str = f"{int(character_id):04d}"
        safe_scene_id = re.sub(r'[<>:"/\\|?*\s]', "_", str(scene_id))[:30]
        pattern = re.compile(
            rf"^[^_]+_{re.escape(character_id_str)}_SCENE_{re.escape(safe_scene_id)}_"
            rf"composite_v\d+_\d{{8}}_\d{{6}}\.(jpg|jpeg|png)$",
            re.IGNORECASE,
        )

        matching_files = []
        for filename in os.listdir(composite_dir):
            if not pattern.match(filename):
                continue
            filepath = os.path.join(composite_dir, filename)
            matching_files.append((filepath, os.path.getmtime(filepath)))

        if not matching_files:
            return None

        matching_files.sort(key=lambda item: item[1], reverse=True)
        return self.validate_composite_image_reference(matching_files[0][0])

    def validate_composite_image_reference(self, reference: str | None) -> str | None:
        """Normalize a composite reference into a public static URL."""

        if not reference:
            return None

        if reference.startswith("/static/images/composite/"):
            composite_dir = self._resolve_dir("COMPOSITE_IMAGE_SAVE_DIR")
            if not composite_dir:
                return None
            filename = unquote(os.path.basename(reference))
            filepath = os.path.join(composite_dir, filename)
            return reference if os.path.exists(filepath) else None

        if os.path.exists(reference):
            filename = quote(os.path.basename(reference), safe="")
            return f"/static/images/composite/{filename}"

        if reference.startswith("/static/"):
            return reference

        return None

    def submit_opening_asset_generation(
        self,
        *,
        executor: Executor | None,
        thread_id: str,
        character_id: int,
        event_scene: str,
        selected_scene_id: str,
        character_image_url: str | None,
    ) -> bool:
        """Queue async story-opening asset generation when no ready composite exists."""

        if (
            executor is None
            or self.image_service is None
            or not getattr(self.image_service, "enabled", False)
        ):
            return False

        if self.find_latest_composite_image_url(
            character_id=character_id,
            scene_id=event_scene,
        ):
            return False

        try:
            executor.submit(
                self.generate_opening_composite_image_async,
                thread_id=thread_id,
                character_id=character_id,
                event_scene=event_scene,
                selected_scene_id=selected_scene_id,
                character_image_url=character_image_url,
            )
            return True
        except Exception as exc:
            logger.warning(
                "failed to submit story asset task: thread_id=%s scene_id=%s error=%s",
                thread_id,
                event_scene,
                str(exc),
                exc_info=True,
            )
            return False

    def generate_opening_composite_image_async(
        self,
        *,
        thread_id: str,
        character_id: int,
        event_scene: str,
        selected_scene_id: str,
        character_image_url: str | None = None,
    ) -> str | None:
        """Generate story-opening media in the background.

        The runtime does not block on this task. A later refresh or recovery reads the
        generated asset from disk and normalizes it through the same contract.
        """

        if self.image_service is None:
            return None

        try:
            scene_image_path = self.image_service.get_latest_scene_image_path(event_scene)
            scene_image_url = None

            if scene_image_path and os.path.exists(scene_image_path):
                scene_image_url = self._scene_path_to_url(scene_image_path)
            else:
                from data.scenes import SUB_SCENES

                logger.info(
                    "generating story scene image: thread_id=%s scene_id=%s selected_scene_id=%s",
                    thread_id,
                    event_scene,
                    selected_scene_id,
                )
                scene_info = SUB_SCENES.get(event_scene, {})
                scene_data = {
                    "scene_id": event_scene,
                    "scene_name": scene_info.get("name", event_scene),
                    "scene_description": scene_info.get("description", ""),
                }
                scene_image_url = self.image_service.generate_scene_image(scene_data, event_scene)
                scene_image_path = self.image_service.get_latest_scene_image_path(event_scene)

            if not scene_image_url and not scene_image_path:
                logger.warning(
                    "scene image generation failed: thread_id=%s scene_id=%s",
                    thread_id,
                    event_scene,
                )
                return None

            character_image_path = self._resolve_character_image_path(
                character_id=character_id,
                character_image_url=character_image_url,
            )
            if not character_image_path:
                logger.warning(
                    "character image missing for composite generation: thread_id=%s character_id=%s",
                    thread_id,
                    character_id,
                )
                return None

            usable_scene_path = scene_image_path
            if usable_scene_path and not os.path.exists(usable_scene_path):
                usable_scene_path = scene_image_url

            composite_path = self.image_service.composite_scene_with_character(
                scene_image_path=usable_scene_path or scene_image_url,
                character_image_path=character_image_path,
                character_id=character_id,
                scene_id=event_scene,
                user_id=None,
            )
            composite_url = self.validate_composite_image_reference(composite_path)
            if composite_url:
                logger.info(
                    "story composite image ready: thread_id=%s scene_id=%s url=%s",
                    thread_id,
                    event_scene,
                    composite_url,
                )
            return composite_url
        except Exception as exc:
            logger.error(
                "story composite generation failed: thread_id=%s character_id=%s scene_id=%s error=%s",
                thread_id,
                character_id,
                event_scene,
                str(exc),
                exc_info=True,
            )
            return None

    def _resolve_character_image_path(
        self,
        *,
        character_id: int,
        character_image_url: str | None,
    ) -> str | None:
        if self.image_service is None:
            return None

        if character_image_url:
            if any(token in character_image_url for token in ("portrait_img1", "portrait_img2", "portrait_img3")):
                transparent_path = self.image_service.remove_background_with_rembg(
                    image_path=character_image_url,
                    character_id=character_id,
                    rename_to_standard=False,
                )
                return transparent_path or character_image_url
            return character_image_url

        return self.image_service.get_latest_character_image_path(character_id)

    def _normalize_asset_resource(
        self,
        *,
        asset_type: str,
        payload: Dict[str, Any] | None,
        fallback_url: str | None,
        fallback_pending: bool,
    ) -> Dict[str, Any]:
        source = dict(payload or {})
        url = source["url"] if "url" in source else fallback_url
        status = str(source.get("status") or "").strip().lower()
        if status not in {self.READY, self.PENDING, self.FAILED}:
            status = self._infer_status(url=url, pending=fallback_pending)

        normalized = {
            "type": asset_type,
            "status": status,
            "url": url,
        }

        detail = source.get("detail")
        if detail:
            normalized["detail"] = str(detail)
        elif status == self.PENDING:
            normalized["detail"] = "generation_pending"
        elif status == self.FAILED:
            normalized["detail"] = "not_available"
        return normalized

    def _build_asset_resource(
        self,
        *,
        asset_type: str,
        url: str | None,
        pending: bool,
    ) -> Dict[str, Any]:
        status = self._infer_status(url=url, pending=pending)
        payload = {
            "type": asset_type,
            "status": status,
            "url": url,
        }
        if status == self.PENDING:
            payload["detail"] = "generation_pending"
        elif status == self.FAILED:
            payload["detail"] = "not_available"
        return payload

    def _infer_status(
        self,
        *,
        url: str | None,
        pending: bool,
    ) -> str:
        if url:
            return self.READY
        if pending:
            return self.PENDING
        return self.FAILED

    @staticmethod
    def _backend_root() -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _resolve_dir(self, config_attr: str) -> str | None:
        import config

        raw_path = getattr(config, config_attr, None)
        if not raw_path:
            return None
        if os.path.isabs(raw_path):
            return os.path.normpath(raw_path)
        return os.path.normpath(os.path.join(self._backend_root(), raw_path))

    def _scene_path_to_url(self, scene_image_path: str) -> str:
        filename = quote(os.path.basename(scene_image_path), safe="")
        small_scene_dir = self._resolve_dir("SMALL_SCENE_IMAGE_SAVE_DIR")
        if small_scene_dir:
            normalized_scene_path = os.path.normpath(os.path.abspath(scene_image_path))
            normalized_small_scene_dir = os.path.normpath(os.path.abspath(small_scene_dir))
            if os.path.exists(small_scene_dir) and normalized_scene_path.startswith(normalized_small_scene_dir):
                return f"/static/images/smallscenes/{filename}"
        return f"/static/images/scenes/{filename}"

    def _lookup_fallback_scene_image_url(self, scene_id: str) -> str | None:
        import config
        from data.scenes import MAJOR_SCENES, SUB_SCENES, get_major_scene_by_sub_scene

        major_scene_id = get_major_scene_by_sub_scene(scene_id)
        scene_info = SUB_SCENES.get(scene_id, {})
        scene_name = scene_info.get("name", scene_id)
        major_scene_name = MAJOR_SCENES.get(major_scene_id, {}).get("name", major_scene_id)

        scene_images_dir = self._resolve_dir("SCENE_IMAGE_SAVE_DIR")
        if not scene_images_dir or not os.path.exists(scene_images_dir):
            return None

        patterns = [
            f"{scene_id}_{scene_name}.*",
            f"{major_scene_id}_{major_scene_name}.*",
            f"{scene_id}.*",
            f"{major_scene_id}.*",
        ]
        image_extensions = (".jpg", ".jpeg", ".png", ".webp")
        for pattern in patterns:
            full_pattern = os.path.join(scene_images_dir, pattern)
            matching_files = [
                candidate
                for candidate in glob.glob(full_pattern)
                if candidate.lower().endswith(image_extensions)
            ]
            if not matching_files:
                continue
            latest_file = max(matching_files, key=os.path.getmtime)
            filename = quote(os.path.basename(latest_file), safe="")
            return f"/static/images/scenes/{filename}"
        return None
