"""Story-turn domain service."""

from __future__ import annotations

from concurrent.futures import Executor
import json
from typing import TYPE_CHECKING, Any, Dict

from story.exceptions import (
    DuplicateStoryRoundSubmissionError,
    StorySessionNotFoundError,
    StorySessionRestoreFailedError,
)
from story.story_asset_service import StoryAssetService
from story.story_response_utils import (
    attach_snapshot_metadata,
    build_duplicate_story_round_response,
    states_to_payload,
)
from utils.logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from story.story_session_service import StorySessionService


class StoryTurnService:
    """Own story initialization and round submission orchestration."""

    def __init__(
        self,
        *,
        session_manager,
        character_service,
        story_session_service: "StorySessionService | None" = None,
        story_asset_service: StoryAssetService | None = None,
        image_executor: Executor | None = None,
    ):
        self.session_manager = session_manager
        self.character_service = character_service
        self.story_session_service = story_session_service
        self.story_asset_service = story_asset_service or StoryAssetService()
        self.image_executor = image_executor

    def submit_turn(
        self,
        *,
        thread_id: str,
        user_input: str,
        option_id: int | None,
        user_id: str | None,
        character_id: str | int | None,
    ) -> Dict[str, Any]:
        """Submit a story turn with locking and restore handled in the domain layer."""

        try:
            return self._process_input_with_session_lock(
                thread_id=thread_id,
                user_input=user_input,
                option_id=option_id,
            )
        except StorySessionNotFoundError:
            if character_id in (None, ""):
                raise
            if self.story_session_service is None:
                raise StorySessionRestoreFailedError(thread_id=thread_id)

            try:
                character_id_int = int(character_id)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"character_id must be an integer: {character_id}") from exc

            try:
                init_result = self.story_session_service.init_game(
                    user_id=user_id,
                    character_id=character_id_int,
                    game_mode="solo",
                )
                new_thread_id = init_result["thread_id"]
                restored_story = self.initialize_story(new_thread_id, character_id_int)

                if option_id is not None:
                    restored_story["thread_id"] = new_thread_id
                    restored_story["session_restored"] = True
                    restored_story["need_reselect_option"] = True
                    restored_story["restored_from_thread_id"] = thread_id
                    return restored_story

                result = self._process_input_with_session_lock(
                    thread_id=new_thread_id,
                    user_input=user_input,
                    option_id=option_id,
                )
                result["thread_id"] = new_thread_id
                result["session_restored"] = True
                result["restored_from_thread_id"] = thread_id
                return result
            except Exception as exc:
                logger.error(
                    "story session restore failed: thread_id=%s character_id=%s error=%s",
                    thread_id,
                    character_id_int,
                    str(exc),
                    exc_info=True,
                )
                raise StorySessionRestoreFailedError(
                    thread_id=thread_id,
                    character_id=character_id_int,
                ) from exc

    def initialize_story(
        self,
        thread_id: str,
        character_id: int,
        scene_id: str = "school",
        character_image_url: str | None = None,
        opening_event_id: str | None = None,
    ) -> Dict[str, Any]:
        logger.info(
            "story initialize requested: thread_id=%s character_id=%s scene_id=%s",
            thread_id,
            character_id,
            scene_id,
        )

        session = self.session_manager.get_session(thread_id)
        if not session:
            raise StorySessionNotFoundError(thread_id=thread_id)

        if session.character_id != character_id:
            raise ValueError("Character ID mismatch")

        latest_snapshot = self.session_manager.get_latest_snapshot(thread_id)
        if session.is_initialized and latest_snapshot is not None:
            logger.info(
                "story initialize idempotent hit: thread_id=%s round_no=%s",
                thread_id,
                latest_snapshot.round_no,
            )
            payload = dict(latest_snapshot.response_payload or {})
            if self.story_session_service is not None:
                payload = self.story_session_service.refresh_story_response_payload(
                    thread_id=thread_id,
                    payload=payload,
                )
            return attach_snapshot_metadata(
                payload=self.story_asset_service.merge_story_assets(payload),
                round_no=latest_snapshot.round_no,
                status=latest_snapshot.status,
                snapshot_record=latest_snapshot,
                thread_id=thread_id,
            )

        event = session.story_engine.get_opening_event(
            character_id=character_id,
            scene_id=scene_id,
            opening_event_id=opening_event_id,
        )
        event_scene = event.get("scene", scene_id)
        session.story_engine.current_scene = event_scene
        session.is_initialized = True

        dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
        session.current_dialogue_round = dialogue_data
        session.story_engine.record_character_dialogue(dialogue_data["character_dialogue"])

        scene_image_url = self.story_asset_service.resolve_scene_image_url(event_scene)
        composite_image_url = self.story_asset_service.find_latest_composite_image_url(
            character_id=character_id,
            scene_id=event_scene,
        )
        composite_image_pending = False
        if composite_image_url is None:
            composite_image_pending = self.story_asset_service.submit_opening_asset_generation(
                executor=self.image_executor,
                thread_id=thread_id,
                character_id=character_id,
                event_scene=event_scene,
                selected_scene_id=scene_id,
                character_image_url=character_image_url,
            )

        response_payload = {
            "event_title": event.get("title", "初遇"),
            "story_background": event.get("story_background", ""),
            "scene": event_scene,
            "character_dialogue": dialogue_data["character_dialogue"],
            "player_options": dialogue_data["player_options"],
            "composite_image_url": composite_image_url,
            "scene_image_url": scene_image_url,
            "current_states": states_to_payload(
                session.db_manager.get_character_states(character_id)
            ),
        }
        response_payload = self.story_asset_service.merge_story_assets(
            response_payload,
            scene_pending=scene_image_url is None and composite_image_pending,
            composite_pending=composite_image_pending and composite_image_url is None,
        )

        try:
            snapshot_record = self.session_manager.save_story_snapshot(
                session=session,
                round_no=0,
                response_payload=response_payload,
                status="in_progress",
            )
        except Exception:
            self.session_manager.evict_runtime_session(thread_id)
            raise

        return attach_snapshot_metadata(
            payload=response_payload,
            round_no=0,
            status="in_progress",
            snapshot_record=snapshot_record,
            thread_id=thread_id,
        )

    def process_input(
        self,
        thread_id: str,
        user_input: str,
        option_id: int | None = None,
    ) -> Dict[str, Any]:
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise StorySessionNotFoundError(thread_id=thread_id)

        if not session.is_initialized:
            raise ValueError("Game not initialized. Call initialize_story first.")

        character_id = session.character_id
        session_record = self.session_manager.get_session_record(thread_id)
        round_no = int(getattr(session_record, "current_round_no", 0) or 0) + 1
        state_before = states_to_payload(
            session.db_manager.get_character_states(character_id)
        ) or {}
        dialogue_round_to_persist = None
        dialogue_state_changes = {}

        if option_id is not None:
            if not session.current_dialogue_round:
                raise ValueError("No active dialogue round found. Please request options again.")

            options = session.current_dialogue_round.get("player_options", [])
            if not options:
                raise ValueError("No available options in current dialogue round.")
            if not 0 <= option_id < len(options):
                raise ValueError(
                    f"Invalid option_id: {option_id}. Valid range: 0 to {len(options) - 1}"
                )

            selected_option = options[option_id]
            session.story_engine.process_player_choice(
                character_id=character_id,
                choice=selected_option,
            )
            dialogue_round_to_persist = len(session.story_engine.dialogue_history) // 2
            dialogue_state_changes = (
                selected_option.get("state_changes", {})
                if isinstance(selected_option, dict)
                else {}
            )
        else:
            temp_option = {
                "id": 2,
                "text": user_input or "继续",
                "type": "neutral",
                "state_changes": {},
            }
            session.story_engine.process_player_choice(
                character_id=character_id,
                choice=temp_option,
            )

        try:
            should_continue = session.story_engine.should_continue_dialogue(character_id)
        except Exception as exc:
            logger.error(
                "failed to determine dialogue continuation: thread_id=%s round_no=%s error=%s",
                thread_id,
                round_no,
                str(exc),
                exc_info=True,
            )
            should_continue = True

        response_data = {
            "character_dialogue": None,
            "player_options": None,
            "story_background": None,
            "event_title": None,
            "scene": None,
            "current_states": states_to_payload(
                session.db_manager.get_character_states(character_id)
            ),
            "is_event_finished": False,
            "is_game_finished": False,
        }

        if should_continue:
            dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
            session.current_dialogue_round = dialogue_data
            session.story_engine.record_character_dialogue(dialogue_data["character_dialogue"])

            current_event = session.story_engine.current_event
            self._print_dialogue_info(
                character_id,
                current_event,
                dialogue_data,
                db_manager=session.db_manager,
            )

            current_scene = current_event.get("scene") if current_event else None
            response_data.update(
                {
                    "character_dialogue": dialogue_data["character_dialogue"],
                    "player_options": dialogue_data["player_options"],
                    "story_background": current_event.get("story_background") if current_event else None,
                    "event_title": current_event.get("title") if current_event else None,
                    "scene": current_scene,
                    "scene_image_url": self.story_asset_service.resolve_scene_image_url(current_scene),
                    "current_states": states_to_payload(
                        session.db_manager.get_character_states(character_id)
                    ),
                }
            )
        else:
            try:
                session.story_engine.save_event_to_vector_db(character_id)
            except Exception as exc:
                logger.warning(
                    "failed to save story event to vector db: thread_id=%s round_no=%s error=%s",
                    thread_id,
                    round_no,
                    str(exc),
                    exc_info=True,
                )

            if session.story_engine.is_game_finished():
                ending_event = session.story_engine.get_ending_event(character_id)
                dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
                session.current_dialogue_round = dialogue_data
                session.story_engine.record_character_dialogue(dialogue_data["character_dialogue"])

                self._print_dialogue_info(
                    character_id,
                    ending_event,
                    dialogue_data,
                    db_manager=session.db_manager,
                )

                response_data.update(
                    {
                        "character_dialogue": dialogue_data["character_dialogue"],
                        "player_options": dialogue_data["player_options"],
                        "story_background": ending_event.get("story_background"),
                        "event_title": ending_event.get("title", "结局"),
                        "scene": ending_event.get("scene"),
                        "scene_image_url": self.story_asset_service.resolve_scene_image_url(
                            ending_event.get("scene")
                        ),
                        "composite_image_url": self.story_asset_service.find_latest_composite_image_url(
                            character_id=character_id,
                            scene_id=ending_event.get("scene"),
                        ),
                        "current_states": states_to_payload(
                            session.db_manager.get_character_states(character_id)
                        ),
                        "is_game_finished": True,
                    }
                )
            else:
                next_event = session.story_engine.get_next_event(character_id)
                dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
                session.current_dialogue_round = dialogue_data
                session.story_engine.record_character_dialogue(dialogue_data["character_dialogue"])

                self._print_dialogue_info(
                    character_id,
                    next_event,
                    dialogue_data,
                    db_manager=session.db_manager,
                )

                next_scene = next_event.get("scene")
                response_data.update(
                    {
                        "character_dialogue": dialogue_data["character_dialogue"],
                        "player_options": dialogue_data["player_options"],
                        "story_background": next_event.get("story_background"),
                        "event_title": next_event.get("title"),
                        "scene": next_scene,
                        "scene_image_url": self.story_asset_service.resolve_scene_image_url(next_scene),
                        "composite_image_url": self.story_asset_service.find_latest_composite_image_url(
                            character_id=character_id,
                            scene_id=next_scene,
                        ),
                        "current_states": states_to_payload(
                            session.db_manager.get_character_states(character_id)
                        ),
                        "is_event_finished": True,
                    }
                )

        response_data = self.story_asset_service.merge_story_assets(response_data)
        status = "completed" if response_data.get("is_game_finished") else "in_progress"

        try:
            snapshot_record = self.session_manager.save_story_round(
                session=session,
                round_no=round_no,
                request_payload={
                    "thread_id": thread_id,
                    "user_input": user_input,
                    "option_id": option_id,
                },
                response_payload=response_data,
                user_input_raw=user_input,
                option_id=option_id,
                state_before=state_before,
                status=status,
            )
        except DuplicateStoryRoundSubmissionError:
            logger.info(
                "duplicate story round submission idempotent hit: thread_id=%s round_no=%s",
                thread_id,
                round_no,
            )
            self.session_manager.reload_session(thread_id)
            existing = build_duplicate_story_round_response(
                session_manager=self.session_manager,
                thread_id=thread_id,
                round_no=round_no,
            )
            if existing is not None:
                return self.story_asset_service.merge_story_assets(existing)
            raise ValueError(
                f"duplicate story round submission: thread_id={thread_id}, round_no={round_no}"
            )
        except Exception:
            self.session_manager.reload_session(thread_id)
            raise

        if dialogue_round_to_persist is not None and self.image_executor is not None:
            self.image_executor.submit(
                self._save_dialogue_async,
                session,
                character_id,
                dialogue_round_to_persist,
                dialogue_state_changes,
            )

        return attach_snapshot_metadata(
            payload=response_data,
            round_no=round_no,
            status=status,
            snapshot_record=snapshot_record,
            thread_id=thread_id,
        )

    def _process_input_with_session_lock(
        self,
        *,
        thread_id: str,
        user_input: str,
        option_id: int | None,
    ) -> Dict[str, Any]:
        target_session = self.session_manager.get_session(thread_id)
        if target_session and hasattr(target_session, "lock"):
            with target_session.lock:
                return self.process_input(
                    thread_id=thread_id,
                    user_input=user_input,
                    option_id=option_id,
                )
        return self.process_input(
            thread_id=thread_id,
            user_input=user_input,
            option_id=option_id,
        )

    @staticmethod
    def _save_dialogue_async(session, character_id: int, dialogue_round: int, state_changes: dict):
        try:
            session.story_engine.save_dialogue_round_to_vector_db(
                character_id=character_id,
                dialogue_round=dialogue_round,
                state_changes=state_changes,
            )
        except Exception as exc:
            logger.error(
                "failed to save story dialogue round: character_id=%s round_no=%s error=%s",
                character_id,
                dialogue_round,
                str(exc),
                exc_info=True,
            )

    def _print_dialogue_info(
        self,
        character_id: int,
        event: Dict[str, Any] | None,
        dialogue_data: Dict[str, Any],
        *,
        db_manager=None,
    ):
        """Keep runtime dialogue logging isolated from the main hot path."""

        try:
            active_db_manager = db_manager or self.character_service.db_manager
            character = active_db_manager.get_character(character_id)
            attributes = active_db_manager.get_character_attributes(character_id)
            states = active_db_manager.get_character_states(character_id)

            logger.debug("=" * 80)
            logger.debug("story dialogue trace")
            logger.debug("=" * 80)

            scene = (event or {}).get("scene", "unknown")
            event_title = (event or {}).get("title", "unknown")
            story_background = (event or {}).get("story_background", "")

            logger.debug("scene=%s event=%s", scene, event_title)
            if story_background:
                logger.debug("story_background=%s", story_background[:200])

            if character:
                logger.debug("character=%s gender=%s", character.name, character.gender)
                logger.debug("appearance=%s", character.appearance[:100])
                logger.debug("personality=%s", character.personality[:100])

                if attributes and hasattr(attributes, "appearance_data") and attributes.appearance_data:
                    try:
                        appearance_data = (
                            json.loads(attributes.appearance_data)
                            if isinstance(attributes.appearance_data, str)
                            else attributes.appearance_data
                        )
                        if isinstance(appearance_data, dict) and "keywords" in appearance_data:
                            logger.debug("appearance_keywords=%s", appearance_data["keywords"])
                    except Exception:
                        pass

                if attributes and hasattr(attributes, "personality_data") and attributes.personality_data:
                    try:
                        personality_data = (
                            json.loads(attributes.personality_data)
                            if isinstance(attributes.personality_data, str)
                            else attributes.personality_data
                        )
                        if isinstance(personality_data, dict) and "keywords" in personality_data:
                            logger.debug("personality_keywords=%s", personality_data["keywords"])
                    except Exception:
                        pass

            if states:
                logger.debug(
                    "states favorability=%s trust=%s hostility=%s dependence=%s emotion=%s",
                    states.favorability,
                    states.trust,
                    states.hostility,
                    states.dependence,
                    states.emotion,
                )

            logger.debug("character_dialogue=%s", dialogue_data.get("character_dialogue", ""))
            logger.debug("player_options=%s", dialogue_data.get("player_options", []))
            logger.debug("=" * 80)
        except Exception as exc:
            logger.warning("failed to print story dialogue trace: %s", str(exc), exc_info=True)
