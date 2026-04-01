"""Training-character API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.error_codes import (
    CHARACTER_NOT_FOUND,
    IMAGE_PROCESSING_FAILED,
    INTERNAL_ERROR,
    TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT,
    TRAINING_STORAGE_UNAVAILABLE,
    VALIDATION_ERROR,
)
from api.dependencies import (
    get_character_service,
    get_image_service,
    get_training_character_preview_job_service,
)
from api.response import success_response, error_response, not_found_response
from api.schemas import (
    CharacterImagesResponse,
    TrainingCreateCharacterRequest,
    TrainingCharacterApiResponse,
    TrainingCharacterImagesApiResponse,
    TrainingCharacterPreviewJobApiResponse,
    TrainingCharacterPreviewJobCreateRequest,
    TrainingCharacterRemoveBackgroundApiResponse,
    TrainingCharacterRemoveBackgroundResponse,
    TrainingIdentityPresetListApiResponse,
    TrainingIdentityPresetListResponse,
    RemoveBackgroundRequest,
)
from api.services.character_service import CharacterNotFoundError, CharacterService
from api.services.image_service import ImageService
from api.services.training_character_preview_job_service import (
    TrainingCharacterPreviewCharacterNotFoundError,
    TrainingCharacterPreviewJobConflictError,
    TrainingCharacterPreviewJobInvalidError,
    TrainingCharacterPreviewJobNotFoundError,
    TrainingCharacterPreviewJobService,
)
from api.services.training_identity_preset_service import (
    UnknownTrainingIdentityCodeError,
    list_training_identity_presets,
    resolve_character_request_identity_preset,
)
from training.exceptions import TrainingStorageUnavailableError
from utils.logger import get_logger


router = APIRouter(prefix="/v1/training/characters", tags=["training-characters"])
logger = get_logger(__name__)


def _parse_positive_character_id(raw_character_id: str) -> int | None:
    normalized = str(raw_character_id or "").strip()
    if not normalized or normalized in {"undefined", "null"}:
        return None
    try:
        parsed = int(normalized)
    except ValueError:
        return None
    if parsed <= 0:
        return None
    return parsed


@router.get("/identity-presets", response_model=TrainingIdentityPresetListApiResponse)
async def get_training_identity_presets():
    """List backend-owned identity presets used for training portrait generation."""

    try:
        payload = TrainingIdentityPresetListResponse(presets=list_training_identity_presets())
        return success_response(data=payload.model_dump())
    except Exception as exc:
        logger.error("failed to load training identity presets: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message="failed to load training identity presets",
            error_code=INTERNAL_ERROR,
            details={"route": "training.characters.identity-presets"},
        )


@router.post("/create", response_model=TrainingCharacterApiResponse)
async def create_training_character(
    request: TrainingCreateCharacterRequest,
    character_service: CharacterService = Depends(get_character_service),
):
    """Create training portrait character only (without synchronous image generation)."""

    try:
        if hasattr(request, "model_dump"):
            request_data = request.model_dump(exclude_none=True)
        else:
            request_data = request.dict(exclude_none=True)

        try:
            request_data = resolve_character_request_identity_preset(request_data)
        except UnknownTrainingIdentityCodeError as exc:
            return error_response(
                code=400,
                message=str(exc),
                error_code=VALIDATION_ERROR,
                details={
                    "route": "training.characters.create",
                    "field": "identity_code",
                    "identity_code": exc.identity_code,
                    "supported_identity_codes": list(exc.supported_codes),
                },
            )

        character_id = character_service.create_character(request_data)
        if not character_id or character_id <= 0:
            return error_response(
                code=500,
                message=f"failed to create training character: invalid character id ({character_id})",
                error_code=INTERNAL_ERROR,
                details={"route": "training.characters.create"},
            )

        character_info = character_service.get_character(character_id)
        if "character_id" not in character_info or not character_info.get("character_id"):
            character_info["character_id"] = str(character_id)
        character_info["image_urls"] = character_service.get_character_images(character_id)
        if request_data.get("identity_code"):
            character_info["identity_code"] = request_data.get("identity_code")
        return success_response(data=character_info)
    except TrainingStorageUnavailableError as exc:
        details = {"route": "training.characters.create"}
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=503,
            message=str(exc),
            error_code=TRAINING_STORAGE_UNAVAILABLE,
            details=details,
        )
    except ValueError as exc:
        return error_response(
            code=400,
            message=str(exc),
            error_code=VALIDATION_ERROR,
            details={"route": "training.characters.create"},
        )
    except Exception as exc:
        logger.error("[training.characters] create failed: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"failed to create training character: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.characters.create"},
        )


@router.post("/preview-jobs", response_model=TrainingCharacterPreviewJobApiResponse)
async def create_training_character_preview_job(
    request: TrainingCharacterPreviewJobCreateRequest,
    preview_job_service: TrainingCharacterPreviewJobService = Depends(get_training_character_preview_job_service),
):
    """Create async preview image generation job for an existing training character."""

    try:
        if request.generate_scene_groups:
            return error_response(
                code=400,
                message="generate_scene_groups is disabled in training runtime",
                error_code=VALIDATION_ERROR,
                details={
                    "route": "training.characters.preview_jobs.create",
                    "field": "generate_scene_groups",
                    "reason": "disabled_in_training_runtime",
                },
            )

        record = preview_job_service.create_preview_job(
            character_id=request.character_id,
            idempotency_key=request.idempotency_key,
            user_id=request.user_id,
            image_type=request.image_type,
            group_count=request.group_count,
            generate_scene_groups=request.generate_scene_groups,
            scene_group_count=request.scene_group_count,
            micro_scene_min=request.micro_scene_min,
            micro_scene_max=request.micro_scene_max,
        )
        return success_response(data=record.to_dict())
    except TrainingCharacterPreviewJobConflictError as exc:
        return error_response(
            code=409,
            message=str(exc),
            error_code=TRAINING_CHARACTER_PREVIEW_JOB_CONFLICT,
            details={
                "route": "training.characters.preview_jobs.create",
                "idempotency_key": exc.idempotency_key,
                "existing_job_id": exc.existing_job_id,
            },
        )
    except TrainingCharacterPreviewCharacterNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            details={
                "route": "training.characters.preview_jobs.create",
                "character_id": exc.character_id,
            },
        )
    except TrainingCharacterPreviewJobInvalidError as exc:
        return error_response(
            code=400,
            message=str(exc),
            error_code=VALIDATION_ERROR,
            details={"route": "training.characters.preview_jobs.create"},
        )
    except TrainingStorageUnavailableError as exc:
        details = {"route": "training.characters.preview_jobs.create"}
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=503,
            message=str(exc),
            error_code=TRAINING_STORAGE_UNAVAILABLE,
            details=details,
        )
    except Exception as exc:
        logger.error("[training.characters] preview job create failed: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"failed to create training preview job: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.characters.preview_jobs.create"},
        )


@router.get("/preview-jobs/{job_id}", response_model=TrainingCharacterPreviewJobApiResponse)
async def get_training_character_preview_job(
    job_id: str,
    preview_job_service: TrainingCharacterPreviewJobService = Depends(get_training_character_preview_job_service),
):
    """Poll training character preview job result."""

    try:
        record = preview_job_service.get_preview_job(job_id)
        return success_response(data=record.to_dict())
    except TrainingCharacterPreviewJobNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            details={"route": "training.characters.preview_jobs.get", "job_id": exc.job_id},
        )
    except TrainingStorageUnavailableError as exc:
        details = {"route": "training.characters.preview_jobs.get", "job_id": job_id}
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=503,
            message=str(exc),
            error_code=TRAINING_STORAGE_UNAVAILABLE,
            details=details,
        )
    except Exception as exc:
        logger.error("[training.characters] preview job get failed: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"failed to get training preview job: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.characters.preview_jobs.get", "job_id": job_id},
        )


@router.get("/{character_id}", response_model=TrainingCharacterApiResponse)
async def get_training_character(
    character_id: str,
    character_service: CharacterService = Depends(get_character_service),
):
    """Get training character details."""

    try:
        character_id_int = _parse_positive_character_id(character_id)
        if character_id_int is None:
            return error_response(
                code=400,
                message="invalid character_id",
                error_code=VALIDATION_ERROR,
                details={"route": "training.characters.get", "character_id": character_id},
            )
        character_info = character_service.get_character(character_id_int)
        return success_response(data=character_info)
    except CharacterNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=CHARACTER_NOT_FOUND,
            details={
                "route": "training.characters.get",
                "character_id": getattr(exc, "character_id", character_id),
            },
        )
    except TrainingStorageUnavailableError as exc:
        details = {"route": "training.characters.get", "character_id": character_id}
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=503,
            message=str(exc),
            error_code=TRAINING_STORAGE_UNAVAILABLE,
            details=details,
        )
    except Exception as exc:
        return error_response(
            code=500,
            message=f"failed to get training character: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.characters.get", "character_id": character_id},
        )


@router.get("/{character_id}/images", response_model=TrainingCharacterImagesApiResponse)
async def get_training_character_images(
    character_id: str,
    character_service: CharacterService = Depends(get_character_service),
):
    """Get training character preview image list."""

    try:
        character_id_int = _parse_positive_character_id(character_id)
        if character_id_int is None:
            return error_response(
                code=400,
                message="invalid character_id",
                error_code=VALIDATION_ERROR,
                details={"route": "training.characters.images", "character_id": character_id},
            )

        images = character_service.get_character_images(character_id_int)
        return success_response(data=CharacterImagesResponse(images=images).model_dump())
    except CharacterNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=CHARACTER_NOT_FOUND,
            details={
                "route": "training.characters.images",
                "character_id": getattr(exc, "character_id", character_id),
            },
        )
    except TrainingStorageUnavailableError as exc:
        details = {"route": "training.characters.images", "character_id": character_id}
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=503,
            message=str(exc),
            error_code=TRAINING_STORAGE_UNAVAILABLE,
            details=details,
        )
    except Exception as exc:
        logger.error("[training.characters] get images failed: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"failed to get training character images: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.characters.images", "character_id": character_id},
        )


@router.post(
    "/{character_id}/remove-background",
    response_model=TrainingCharacterRemoveBackgroundApiResponse,
)
async def remove_training_character_background(
    character_id: str,
    request: RemoveBackgroundRequest = RemoveBackgroundRequest(),
    character_service: CharacterService = Depends(get_character_service),
    image_service: ImageService = Depends(get_image_service),
):
    """Remove background for training character preview image."""

    try:
        image_url = request.image_url if request else None
        image_urls = request.image_urls if request else None
        selected_index = request.selected_index if request else None

        character_id_int = _parse_positive_character_id(character_id)
        if character_id_int is None:
            return error_response(
                code=400,
                message="invalid character_id",
                error_code=VALIDATION_ERROR,
                details={"route": "training.characters.remove_background", "character_id": character_id},
            )

        if not image_url:
            images = character_service.get_character_images(character_id_int)
            if not images:
                return not_found_response(
                    message="training character has no preview images",
                    error_code=CHARACTER_NOT_FOUND,
                    details={
                        "route": "training.characters.remove_background",
                        "character_id": character_id_int,
                    },
                )
            image_url = images[0]

        # Background removal is an optional enhancement. If the server lacks rembg/Pillow runtime,
        # fall back to a no-op result (transparent_url == selected_image_url) instead of 500.
        try:
            transparent_path = image_service.remove_background_with_rembg(
                image_path=image_url,
                character_id=character_id_int,
                rename_to_standard=False,
            )
        except RuntimeError as exc:
            reason = str(exc)
            if reason in {"rembg_unavailable", "pillow_unavailable", "rembg_session_unavailable"}:
                transparent_path = None
            else:
                raise

        if not transparent_path:
            deleted_count = 0
            if image_urls and selected_index is not None and len(image_urls) > 1:
                deleted_count = image_service.delete_unselected_character_images(
                    character_id=character_id_int,
                    image_urls=image_urls,
                    selected_index=selected_index,
                )

            response_payload = TrainingCharacterRemoveBackgroundResponse(
                selected_image_url=image_url,
                transparent_url=image_url,
                deleted_count=deleted_count,
            )
            return success_response(data=response_payload.model_dump())

        import os
        from urllib.parse import quote

        filename = os.path.basename(transparent_path)
        result_url = f"/static/images/characters/{quote(filename, safe='')}"

        deleted_count = 0
        if image_urls and selected_index is not None and len(image_urls) > 1:
            deleted_count = image_service.delete_unselected_character_images(
                character_id=character_id_int,
                image_urls=image_urls,
                selected_index=selected_index,
            )

        response_payload = TrainingCharacterRemoveBackgroundResponse(
            selected_image_url=image_url,
            transparent_url=result_url,
            deleted_count=deleted_count,
        )
        return success_response(data=response_payload.model_dump())
    except CharacterNotFoundError as exc:
        return not_found_response(
            message=str(exc),
            error_code=CHARACTER_NOT_FOUND,
            details={
                "route": "training.characters.remove_background",
                "character_id": getattr(exc, "character_id", character_id),
            },
        )
    except TrainingStorageUnavailableError as exc:
        details = {"route": "training.characters.remove_background", "character_id": character_id}
        if exc.details:
            details.update(dict(exc.details))
        return error_response(
            code=503,
            message=str(exc),
            error_code=TRAINING_STORAGE_UNAVAILABLE,
            details=details,
        )
    except Exception as exc:
        logger.error("[training.characters] remove background failed: %s", str(exc), exc_info=True)
        return error_response(
            code=500,
            message=f"failed to process training character background removal: {str(exc)}",
            error_code=INTERNAL_ERROR,
            details={"route": "training.characters.remove_background", "character_id": character_id},
        )
