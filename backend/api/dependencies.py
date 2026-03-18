"""FastAPI 依赖注入定义。

说明：
1. 这里统一维护服务级单例缓存。
2. 具体服务实现改为按需懒加载，避免训练专用服务启动时顺带导入旧剧情流、图片、TTS 等重模块。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from api.services.character_service import CharacterService
    from api.services.game_service import GameService
    from api.services.game_session import GameSessionManager
    from api.services.image_service import ImageService
    from api.services.training_service import TrainingService
    from api.services.tts_service import TTSService


# 服务实例缓存。
# 这里继续保留单例模式，避免每次请求都重新构建 service。
_game_service: Optional[GameService] = None
_character_service: Optional[CharacterService] = None
_image_service: Optional[ImageService] = None
_tts_service: Optional[TTSService] = None
_session_manager: Optional[GameSessionManager] = None
_training_service: Optional[TrainingService] = None


def get_image_service() -> ImageService:
    """获取图片服务实例。"""
    global _image_service
    if _image_service is None:
        # 按需导入，避免训练专用服务启动时提前加载图片相关依赖。
        from api.services.image_service import ImageService

        _image_service = ImageService()
    return _image_service


def get_character_service() -> CharacterService:
    """获取角色服务实例。"""
    global _character_service
    if _character_service is None:
        from api.services.character_service import CharacterService

        image_service = get_image_service()
        _character_service = CharacterService(image_service=image_service)
    return _character_service


def get_game_service() -> GameService:
    """获取剧情服务实例。"""
    global _game_service
    if _game_service is None:
        from api.services.game_service import GameService

        image_service = get_image_service()
        character_service = get_character_service()
        _game_service = GameService(
            character_service=character_service,
            image_service=image_service
        )
    return _game_service


def get_tts_service() -> TTSService:
    """获取 TTS 服务实例。"""
    global _tts_service
    if _tts_service is None:
        from api.services.tts_service import TTSService

        _tts_service = TTSService()
    return _tts_service


def get_session_manager() -> GameSessionManager:
    """获取会话管理器实例。"""
    global _session_manager
    if _session_manager is None:
        from api.services.game_session import GameSessionManager

        _session_manager = GameSessionManager()
    return _session_manager


def get_training_service() -> TrainingService:
    """获取训练服务实例。

    训练服务也走懒加载，方便训练引擎单独启动时只初始化训练域依赖。
    """
    global _training_service
    if _training_service is None:
        from api.services.training_service import TrainingService

        _training_service = TrainingService()
    return _training_service
