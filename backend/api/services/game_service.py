"""游戏服务"""
from typing import Dict, Any, Optional
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from api.services.game_session import GameSessionManager, GameSession
from api.services.character_service import CharacterService
from api.services.image_service import ImageService
from data.scenes import SCENES, SUB_SCENES
from utils.logger import get_logger

logger = get_logger(__name__)
from utils.logger import get_logger

logger = get_logger(__name__)


class GameService:
    """游戏服务"""
    
    def __init__(
        self,
        character_service: Optional[CharacterService] = None,
        image_service: Optional[ImageService] = None,
        session_manager: Optional[GameSessionManager] = None
    ):
        """初始化游戏服务
        
        Args:
            character_service: 角色服务实例，如果为None则自动创建
            image_service: 图片服务实例，如果为None则自动创建
            session_manager: 会话管理器实例，如果为None则自动创建
        """
        self.session_manager = session_manager or GameSessionManager()
        self.character_service = character_service or CharacterService(image_service=image_service)
        self.image_service = image_service or ImageService()
        # 创建线程池用于异步图片生成（最多2个并发）
        self.image_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="image_gen")
    
    def init_game(
        self, 
        user_id: Optional[str], 
        character_id: Optional[int], 
        game_mode: str
    ) -> Dict[str, str]:
        """初始化游戏"""
        logger.info(f"init_game 被调用: user_id={user_id}, character_id={character_id}, game_mode={game_mode}")
        
        if not character_id:
            raise ValueError("character_id is required")
        
        # 创建游戏会话
        logger.debug("正在创建游戏会话...")
        session = self.session_manager.create_session(
            user_id=user_id,
            character_id=character_id,
            game_mode=game_mode
        )
        logger.info(f"游戏会话创建成功: thread_id={session.thread_id}")
        
        return {
            'thread_id': session.thread_id,
            'user_id': session.user_id,
            'game_mode': session.game_mode
        }
    
    def initialize_story(self, thread_id: str, character_id: int, scene_id: str = 'school', 
                         character_image_url: Optional[str] = None, opening_event_id: Optional[str] = None) -> Dict[str, Any]:
        """初始化故事（触发初遇场景）
        
        Args:
            thread_id: 游戏会话ID
            character_id: 角色ID
            scene_id: 初遇大场景ID（玩家选择的大场景，如'school'）
            character_image_url: 用户选择的角色图片URL（可选，如果不提供则使用最新图片）
            opening_event_id: 初遇事件ID（可选，如果不提供则随机选择）
        """
        logger.info(f"initialize_story 被调用: thread_id={thread_id}, character_id={character_id}, scene_id={scene_id}")
        logger.debug(f"当前会话管理器中的会话数量: {len(self.session_manager._sessions)}")
        logger.debug(f"当前会话ID列表: {list(self.session_manager._sessions.keys())}")
        
        session = self.session_manager.get_session(thread_id)
        if not session:
            logger.error(f"会话不存在: thread_id={thread_id}")
            logger.error(f"可用的会话ID: {list(self.session_manager._sessions.keys())}")
            raise ValueError(f"Thread {thread_id} not found")
        
        if session.character_id != character_id:
            raise ValueError("Character ID mismatch")
        
        # 使用玩家选择的场景ID获取开头事件
        if opening_event_id:
            logger.info(f"初始化故事，使用场景: {scene_id}，指定事件: {opening_event_id}")
        else:
            logger.info(f"初始化故事，使用场景: {scene_id}，随机选择事件")
        try:
            event = session.story_engine.get_opening_event(
                character_id=character_id,
                scene_id=scene_id,
                opening_event_id=opening_event_id
            )
            logger.info(f"获取开头事件成功: {event.get('title', '未知')}")
        except Exception as e:
            logger.error(f"获取开头事件失败: {e}", exc_info=True)
            raise
        
        # 更新当前场景（使用事件返回的场景ID，可能因为事件ID对应场景而改变）
        # 例如：school场景的cafeteria事件会使用cafeteria场景
        event_scene = event.get('scene', scene_id)
        session.story_engine.current_scene = event_scene
        logger.debug(f"当前场景设置为: {event_scene} (原始选择: {scene_id})")
        
        session.is_initialized = True
        
        # 获取第一轮对话
        try:
            dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
            session.current_dialogue_round = dialogue_data
            logger.debug(f"获取对话成功，角色对话: {dialogue_data.get('character_dialogue', '')[:50]}...")
            
            # 记录角色对话
            session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
        except Exception as e:
            logger.error(f"获取对话失败: {e}", exc_info=True)
            raise
        
        # 异步生成合成图片（场景+人物）- 不阻塞主流程
        composite_image_url = None
        # 将图片生成任务提交到线程池，不等待完成
        try:
            import os
            import config
            
            if self.image_service.enabled:
                event_scene = event.get('scene', scene_id)
                # 异步生成图片（后台执行，不阻塞响应）
                logger.debug(f"提交图片生成任务到后台（场景: {event_scene}）")
                self.image_executor.submit(
                    self._generate_composite_image_async,
                    thread_id, character_id, event_scene, scene_id, character_image_url
                )
                logger.debug("图片生成任务已提交，继续返回对话数据")
        except Exception as e:
            logger.warning(f"提交图片生成任务失败: {e}", exc_info=True)
        
        # 使用事件返回的场景ID（可能因为事件ID对应场景而改变）
        event_scene = event.get('scene', scene_id)
        
        # 获取场景图片URL（如果已有）
        scene_image_url = None
        try:
            import os
            import config
            from urllib.parse import quote
            
            # 查找最新的场景图片
            logger.debug(f"查找场景图片: scene_id={event_scene}")
            scene_image_path = self.image_service.get_latest_scene_image_path(event_scene)
            logger.debug(f"查找结果: scene_image_path={scene_image_path}")
            
            if scene_image_path and os.path.exists(scene_image_path):
                # URL编码文件名，确保中文文件名能正确访问
                filename = os.path.basename(scene_image_path)
                encoded_filename = quote(filename, safe='')
                
                # 判断图片来自哪个目录，使用对应的URL路径
                import config
                if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR) if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR') else False:
                    small_scene_dir = os.path.normpath(config.SMALL_SCENE_IMAGE_SAVE_DIR)
                elif hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    small_scene_dir = os.path.normpath(os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR))
                else:
                    small_scene_dir = None
                
                # 标准化路径后进行比较，确保路径格式一致
                if small_scene_dir:
                    normalized_scene_path = os.path.normpath(os.path.abspath(scene_image_path))
                    normalized_small_scene_dir = os.path.normpath(os.path.abspath(small_scene_dir))
                    # 检查文件是否在smallscenes目录中
                    if os.path.exists(small_scene_dir) and normalized_scene_path.startswith(normalized_small_scene_dir):
                        scene_image_url = f"/static/images/smallscenes/{encoded_filename}"
                    else:
                        scene_image_url = f"/static/images/scenes/{encoded_filename}"
                else:
                    scene_image_url = f"/static/images/scenes/{encoded_filename}"
                
                logger.debug(f"找到场景图片: 文件名={filename}, URL={scene_image_url}")
            else:
                logger.debug(f"未找到场景图片文件: scene_id={event_scene}, path={scene_image_path}")
                # 如果没有找到，尝试查找简化格式的文件名（用于大场景图片）
                # 格式：{major_scene_id}_{场景名称}.{ext}
                try:
                    from data.scenes import SUB_SCENES, get_major_scene_by_sub_scene
                    major_scene_id = get_major_scene_by_sub_scene(event_scene)
                    scene_info = SUB_SCENES.get(event_scene, {})
                    scene_name = scene_info.get('name', event_scene)
                    
                    # 检查是否有大场景图片文件
                    if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
                        scene_images_dir = config.SCENE_IMAGE_SAVE_DIR
                    else:
                        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        scene_images_dir = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
                    
                    if os.path.exists(scene_images_dir):
                        # 查找格式：{major_scene_id}_{场景名称}.{ext} 或 {scene_id}_{场景名称}.{ext}
                        import glob
                        from data.scenes import MAJOR_SCENES
                        
                        # 获取大场景名称
                        major_scene_name = MAJOR_SCENES.get(major_scene_id, {}).get('name', major_scene_id)
                        
                        # 尝试多种文件名格式
                        patterns = [
                            f"{event_scene}_{scene_name}.*",  # 小场景格式：cafeteria_食堂.*
                            f"{major_scene_id}_{major_scene_name}.*",  # 大场景格式：school_学校.*
                            f"{event_scene}.*",  # 仅场景ID：cafeteria.*
                            f"{major_scene_id}.*"  # 仅大场景ID：school.*
                        ]
                        
                        logger.debug(f"尝试查找场景图片，模式: {patterns}")
                        for pattern in patterns:
                            full_pattern = os.path.join(scene_images_dir, pattern)
                            matching_files = glob.glob(full_pattern)
                            if matching_files:
                                # 过滤出图片文件
                                image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
                                image_files = [f for f in matching_files if any(f.lower().endswith(ext) for ext in image_extensions)]
                                if image_files:
                                    # 使用最新的文件
                                    latest_file = max(image_files, key=os.path.getmtime)
                                    filename = os.path.basename(latest_file)
                                    encoded_filename = quote(filename, safe='')
                                    scene_image_url = f"/static/images/scenes/{encoded_filename}"
                                    logger.debug(f"找到场景图片: 模式={pattern}, 文件名={filename}, URL={scene_image_url}")
                                    break
                        
                        if not scene_image_url:
                            logger.debug(f"未找到任何场景图片文件，场景ID={event_scene}, 大场景ID={major_scene_id}")
                except Exception as e2:
                    logger.warning(f"查找大场景图片失败: {e2}", exc_info=True)
        except Exception as e:
            logger.warning(f"获取场景图片URL失败: {e}", exc_info=True)
        
        # 验证返回的composite_image_url（如果存在且不是None）
        validated_composite_url = None
        if composite_image_url:
            # 如果composite_image_url是文件路径，需要验证并转换为URL
            if composite_image_url.startswith('/') and not composite_image_url.startswith('/static/'):
                # 可能是文件路径，需要验证
                validated_composite_url = self._validate_composite_image_url(composite_image_url)
            elif composite_image_url.startswith('/static/images/composite/'):
                # 已经是URL格式，验证文件是否存在
                import os
                import config
                from urllib.parse import unquote
                filename = unquote(os.path.basename(composite_image_url))
                if os.path.isabs(config.COMPOSITE_IMAGE_SAVE_DIR):
                    composite_dir = config.COMPOSITE_IMAGE_SAVE_DIR
                else:
                    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    composite_dir = os.path.join(backend_dir, config.COMPOSITE_IMAGE_SAVE_DIR)
                filepath = os.path.join(composite_dir, filename)
                if os.path.exists(filepath):
                    validated_composite_url = composite_image_url
                    logger.debug(f"合成图片URL验证成功: {composite_image_url} -> {filepath}")
                else:
                    logger.error(f"合成图片URL对应的文件不存在: {composite_image_url} -> {filepath}")
                    validated_composite_url = None
            else:
                validated_composite_url = composite_image_url
        
        return {
            'event_title': event.get('title', '初遇'),
            'story_background': event.get('story_background', ''),
            'scene': event_scene,  # 返回事件对应的场景ID（可能不同于玩家选择的场景ID）
            'character_dialogue': dialogue_data['character_dialogue'],
            'player_options': dialogue_data['player_options'],
            'composite_image_url': validated_composite_url,  # 合成后的游戏场景图片（已验证，可能为None）
            'scene_image_url': scene_image_url  # 场景图片URL（如果已有）
        }
    
    def _validate_composite_image_url(self, filepath: str) -> Optional[str]:
        """验证合成图片文件并返回正确的URL
        
        Args:
            filepath: 合成图片的本地文件路径
            
        Returns:
            如果文件存在，返回URL编码后的静态文件URL；否则返回None
        """
        if not filepath:
            return None
        
        try:
            import os
            from urllib.parse import quote
            
            # 验证文件存在
            if not os.path.exists(filepath):
                logger.error(f"合成图片文件不存在: {filepath}")
                return None
            
            # 获取文件名并URL编码
            filename = os.path.basename(filepath)
            encoded_filename = quote(filename, safe='')
            composite_url = f"/static/images/composite/{encoded_filename}"
            
            # 再次验证文件确实存在（双重检查）
            if os.path.exists(filepath):
                logger.debug(f"合成图片URL验证成功: {filepath} -> {composite_url}")
                return composite_url
            else:
                logger.error(f"合成图片文件验证失败: {filepath}")
                return None
        except Exception as e:
            logger.error(f"验证合成图片URL失败: {e}", exc_info=True)
            return None
    
    def _generate_composite_image_async(self, thread_id: str, character_id: int, 
                                        event_scene: str, scene_id: str, 
                                        character_image_url: Optional[str] = None):
        """异步生成合成图片（在后台线程中执行）"""
        try:
            import os
            import config
            from data.scenes import SUB_SCENES
            
            # 优化：先检查是否已有场景图片（复用已有图片，节省时间）
            scene_image_path = self.image_service.get_latest_scene_image_path(event_scene)
            scene_image_url = None
            
            if scene_image_path and os.path.exists(scene_image_path):
                # 已有场景图片，直接使用
                logger.debug(f"复用已有场景图片: {scene_image_path}")
                # URL编码文件名，确保中文文件名能正确访问
                from urllib.parse import quote
                import config
                encoded_filename = quote(os.path.basename(scene_image_path), safe='')
                
                # 判断图片来自哪个目录，使用对应的URL路径
                if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                    if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                        small_scene_dir = os.path.normpath(config.SMALL_SCENE_IMAGE_SAVE_DIR)
                    else:
                        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                        small_scene_dir = os.path.normpath(os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR))
                    
                    # 标准化路径后进行比较，确保路径格式一致
                    normalized_scene_path = os.path.normpath(os.path.abspath(scene_image_path))
                    normalized_small_scene_dir = os.path.normpath(os.path.abspath(small_scene_dir))
                    
                    # 检查文件是否在smallscenes目录中
                    if os.path.exists(small_scene_dir) and normalized_scene_path.startswith(normalized_small_scene_dir):
                        scene_image_url = f"/static/images/smallscenes/{encoded_filename}"
                    else:
                        scene_image_url = f"/static/images/scenes/{encoded_filename}"
                else:
                    scene_image_url = f"/static/images/scenes/{encoded_filename}"
            else:
                # 没有已有图片，生成新图片
                logger.info(f"开始生成场景图片: {event_scene}")
                scene_info = SUB_SCENES.get(event_scene, {})
                scene_data = {
                    'scene_id': event_scene,
                    'scene_name': scene_info.get('name', event_scene),
                    'scene_description': scene_info.get('description', '')
                }
                scene_image_url = self.image_service.generate_scene_image(scene_data, event_scene)
            
            if scene_image_url:
                # 如果刚生成新图片，获取其本地路径并更新URL
                if not scene_image_path or not os.path.exists(scene_image_path):
                    scene_image_path = self.image_service.get_latest_scene_image_path(event_scene)
                    if scene_image_path and os.path.exists(scene_image_path):
                        # 重新构建URL，确保使用正确的路径
                        from urllib.parse import quote
                        import config
                        encoded_filename = quote(os.path.basename(scene_image_path), safe='')
                        
                        # 判断图片来自哪个目录
                        if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                            if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                                small_scene_dir = os.path.normpath(config.SMALL_SCENE_IMAGE_SAVE_DIR)
                            else:
                                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                small_scene_dir = os.path.normpath(os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR))
                            
                            # 标准化路径后进行比较，确保路径格式一致
                            normalized_scene_path = os.path.normpath(os.path.abspath(scene_image_path))
                            normalized_small_scene_dir = os.path.normpath(os.path.abspath(small_scene_dir))
                            
                            if os.path.exists(small_scene_dir) and normalized_scene_path.startswith(normalized_small_scene_dir):
                                scene_image_url = f"/static/images/smallscenes/{encoded_filename}"
                            else:
                                scene_image_url = f"/static/images/scenes/{encoded_filename}"
                        else:
                            scene_image_url = f"/static/images/scenes/{encoded_filename}"
                if not scene_image_path:
                    scene_image_path = scene_image_url
                
                character_image_path = None
                if character_image_url:
                    logger.debug(f"用户选择的角色图片: {character_image_url}")
                    # 检查是否已经是透明背景图片（在remove_character_background中已处理）
                    # 如果character_image_url包含_img1/img2/img3，说明是原始图片，需要处理
                    # 否则可能是已经处理过的透明图片
                    if 'portrait_img1' in character_image_url or 'portrait_img2' in character_image_url or 'portrait_img3' in character_image_url:
                        # 原始组图，需要处理透明背景
                        logger.debug("检测到原始组图，开始处理透明背景...")
                        transparent_path = self.image_service.remove_background_with_rembg(
                            image_path=character_image_url,
                            character_id=character_id,
                            rename_to_standard=False  # 使用基于原文件名的命名逻辑
                        )
                        
                        if transparent_path:
                            character_image_path = transparent_path
                            logger.debug(f"透明背景处理成功: {transparent_path}")
                        else:
                            logger.warning(f"透明背景处理失败，使用原图: {character_image_url}")
                            character_image_path = character_image_url
                    else:
                        # 可能已经是透明背景图片，直接使用
                        logger.debug(f"使用已处理的透明背景图片: {character_image_url}")
                        character_image_path = character_image_url
                else:
                    # 如果没有提供图片URL，尝试获取最新保存的透明图片
                    character_image_path = self.image_service.get_latest_character_image_path(character_id)
                    if character_image_path:
                        logger.debug(f"使用最新保存的角色图片: {character_image_path}")
                    else:
                        logger.debug("未找到角色图片，跳过合成")
                
                if character_image_path:
                    logger.debug("开始合成图片...")
                    if scene_image_path and isinstance(scene_image_path, str) and not scene_image_path.startswith('http'):
                        if not os.path.exists(scene_image_path):
                            scene_image_path = scene_image_url
                    else:
                        scene_image_path = scene_image_url
                    
                    composite_path = self.image_service.composite_scene_with_character(
                        scene_image_path=scene_image_path,
                        character_image_path=character_image_path,
                        character_id=character_id,
                        scene_id=event_scene,
                        user_id=None
                    )
                    
                    if composite_path:
                        # 验证并构建正确的URL
                        composite_image_url = self._validate_composite_image_url(composite_path)
                        if composite_image_url:
                            logger.info(f"合成图片生成成功: {composite_path} -> {composite_image_url}")
                        else:
                            logger.error(f"合成图片URL验证失败: {composite_path}")
                    else:
                        logger.warning(f"合成图片生成失败: composite_path={composite_path}")
                else:
                    logger.warning(f"未找到角色图片 (character_id: {character_id})")
            else:
                logger.warning("场景图片生成失败")
        except Exception as e:
            logger.error(f"生成合成图片失败: {e}", exc_info=True)
    
    def _save_dialogue_async(self, session, character_id: int, dialogue_round: int, state_changes: dict):
        """异步保存对话轮次到向量数据库（在后台线程中执行）"""
        try:
            session.story_engine.save_dialogue_round_to_vector_db(
                character_id=character_id,
                dialogue_round=dialogue_round,
                state_changes=state_changes
            )
            logger.debug(f"对话轮次保存成功 (round: {dialogue_round})")
        except Exception as e:
            logger.error(f"保存对话轮次失败: {e}", exc_info=True)
    
    def process_input(
        self, 
        thread_id: str, 
        user_input: str, 
        option_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """处理玩家输入"""
        session = self.session_manager.get_session(thread_id)
        if not session:
            # 会话不存在，尝试从请求中获取character_id重新创建
            # 注意：这里需要前端传递character_id，或者从其他地方恢复
            raise ValueError(f"Thread {thread_id} not found. 会话可能已过期，请重新初始化游戏。")
        
        if not session.is_initialized:
            raise ValueError("Game not initialized. Call initialize_story first.")
        
        character_id = session.character_id
        
        # 如果提供了option_id，使用选项；否则使用user_input作为自由输入
        if option_id is not None:
            if not session.current_dialogue_round:
                raise ValueError("No active dialogue round found. Please request options again.")

            # 从当前对话轮次中选择选项
            options = session.current_dialogue_round.get('player_options', [])
            if not options:
                raise ValueError("No available options in current dialogue round.")

            if 0 <= option_id < len(options):
                selected_option = options[option_id]
                
                # 输出玩家选择
                option_text = selected_option.get('text', '') if isinstance(selected_option, dict) else str(selected_option)
                logger.debug(f"玩家选择 选项 {option_id + 1}: {option_text}")
                if isinstance(selected_option, dict) and selected_option.get('state_changes'):
                    logger.debug(f"  - 状态变化: {selected_option.get('state_changes')}")
                
                # 处理玩家选择
                try:
                    session.story_engine.process_player_choice(
                        character_id=character_id,
                        choice=selected_option
                    )
                except Exception as e:
                    logger.error(f"处理玩家选择失败: {e}", exc_info=True)
                    raise
                
                # 异步保存对话轮次到向量数据库（不阻塞主流程）
                dialogue_round = len(session.story_engine.dialogue_history) // 2
                state_changes = selected_option.get('state_changes', {}) if isinstance(selected_option, dict) else {}
                # 提交到线程池异步执行，不等待完成
                self.image_executor.submit(
                    self._save_dialogue_async,
                    session, character_id, dialogue_round, state_changes
                )
            else:
                raise ValueError(
                    f"Invalid option_id: {option_id}. Valid range: 0 to {len(options) - 1}"
                )
        else:
            # 自由输入（创建中性选项）
            logger.debug(f"玩家输入 自由文本: {user_input}")
            
            temp_option = {
                'id': 2,
                'text': user_input or "继续",
                'type': 'neutral',
                'state_changes': {}
            }
            try:
                session.story_engine.process_player_choice(
                    character_id=character_id,
                    choice=temp_option
                )
            except Exception as e:
                logger.error(f"处理自由输入失败: {e}", exc_info=True)
                raise
        
        # 检查是否应该继续当前事件的对话（AI判断）
        try:
            should_continue = session.story_engine.should_continue_dialogue(character_id)
        except Exception as e:
            logger.error(f"检查是否继续对话失败: {e}", exc_info=True)
            # 如果检查失败，默认继续对话
            should_continue = True
        
        # 获取当前状态值（全部12个）
        states = session.db_manager.get_character_states(character_id)
        current_states = None
        if states:
            current_states = {
                'favorability': states.favorability,
                'trust': states.trust,
                'hostility': states.hostility,
                'dependence': states.dependence,
                'emotion': states.emotion,
                'stress': states.stress,
                'anxiety': states.anxiety,
                'happiness': states.happiness,
                'sadness': states.sadness,
                'confidence': states.confidence,
                'initiative': states.initiative,
                'caution': states.caution
            }
        
        response_data = {
            'character_dialogue': None,
            'player_options': None,
            'story_background': None,
            'event_title': None,
            'scene': None,
            'current_states': current_states,  # 添加全部12个状态值
            'is_event_finished': False,
            'is_game_finished': False
        }
        
        if should_continue:
            # 继续当前事件的对话
            try:
                dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
                session.current_dialogue_round = dialogue_data
                session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
            except Exception as e:
                logger.error(f"获取下一轮对话失败: {e}", exc_info=True)
                raise
            
            # 输出详细信息到控制台
            self._print_dialogue_info(character_id, session.story_engine.current_event, dialogue_data)
            
            # 更新状态值
            states = session.db_manager.get_character_states(character_id)
            if states:
                current_states = {
                    'favorability': states.favorability,
                    'trust': states.trust,
                    'hostility': states.hostility,
                    'dependence': states.dependence,
                    'emotion': states.emotion,
                    'stress': states.stress,
                    'anxiety': states.anxiety,
                    'happiness': states.happiness,
                    'sadness': states.sadness,
                    'confidence': states.confidence,
                    'initiative': states.initiative,
                    'caution': states.caution
                }
            else:
                current_states = None
            
            # 获取场景图片URL（如果场景切换时已生成）
            scene_image_url = None
            current_scene = session.story_engine.current_event.get('scene') if session.story_engine.current_event else None
            if current_scene:
                try:
                    import os
                    import config
                    from urllib.parse import quote
                    
                    # 查找最新的场景图片
                    scene_image_path = self.image_service.get_latest_scene_image_path(current_scene)
                    if scene_image_path and os.path.exists(scene_image_path):
                        # URL编码文件名，确保中文文件名能正确访问
                        encoded_filename = quote(os.path.basename(scene_image_path), safe='')
                        
                        # 判断图片来自哪个目录，使用对应的URL路径
                        if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                            if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                                small_scene_dir = os.path.normpath(config.SMALL_SCENE_IMAGE_SAVE_DIR)
                            else:
                                backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                small_scene_dir = os.path.normpath(os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR))
                            
                            # 标准化路径后进行比较，确保路径格式一致
                            normalized_scene_path = os.path.normpath(os.path.abspath(scene_image_path))
                            normalized_small_scene_dir = os.path.normpath(os.path.abspath(small_scene_dir))
                            
                            # 检查文件是否在smallscenes目录中
                            if os.path.exists(small_scene_dir) and normalized_scene_path.startswith(normalized_small_scene_dir):
                                scene_image_url = f"/static/images/smallscenes/{encoded_filename}"
                            else:
                                scene_image_url = f"/static/images/scenes/{encoded_filename}"
                        else:
                            scene_image_url = f"/static/images/scenes/{encoded_filename}"
                        logger.debug(f"找到场景图片: {scene_image_url} (路径: {scene_image_path})")
                except Exception as e:
                    logger.warning(f"获取场景图片URL失败: {e}", exc_info=True)
            
            response_data.update({
                'character_dialogue': dialogue_data['character_dialogue'],
                'player_options': dialogue_data['player_options'],
                'story_background': session.story_engine.current_event.get('story_background') if session.story_engine.current_event else None,
                'event_title': session.story_engine.current_event.get('title') if session.story_engine.current_event else None,
                'scene': current_scene,
                'scene_image_url': scene_image_url,  # 场景图片URL（用于前端显示）
                'current_states': current_states,  # 更新状态值
            })
        else:
            # 当前事件对话结束，保存事件并进入下一个事件
            try:
                session.story_engine.save_event_to_vector_db(character_id)
            except Exception as e:
                # 向量库属于增强能力，失败不应中断主流程
                logger.warning(f"保存事件到向量数据库失败，已跳过: {e}", exc_info=True)
            
            # 检查游戏是否结束
            if session.story_engine.is_game_finished():
                # 获取结尾事件
                try:
                    ending_event = session.story_engine.get_ending_event(character_id)
                    dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
                    session.current_dialogue_round = dialogue_data
                    session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
                except Exception as e:
                    logger.error(f"获取结尾事件对话失败: {e}", exc_info=True)
                    raise
                
                # 输出详细信息到控制台
                self._print_dialogue_info(character_id, ending_event, dialogue_data)
                
                # 更新状态值
                states = session.db_manager.get_character_states(character_id)
                if states:
                    current_states = {
                        'favorability': states.favorability,
                        'trust': states.trust,
                        'hostility': states.hostility,
                        'dependence': states.dependence,
                        'emotion': states.emotion,
                        'stress': states.stress,
                        'anxiety': states.anxiety,
                        'happiness': states.happiness,
                        'sadness': states.sadness,
                        'confidence': states.confidence,
                        'initiative': states.initiative,
                        'caution': states.caution
                    }
                else:
                    current_states = None
                
                response_data.update({
                    'character_dialogue': dialogue_data['character_dialogue'],
                    'player_options': dialogue_data['player_options'],
                    'story_background': ending_event.get('story_background'),
                    'event_title': ending_event.get('title', '结局'),
                    'scene': ending_event.get('scene'),
                    'current_states': current_states,  # 更新状态值
                    'is_game_finished': True
                })
            else:
                # 获取下一个事件
                try:
                    next_event = session.story_engine.get_next_event(character_id)
                    dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
                    session.current_dialogue_round = dialogue_data
                    session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
                except Exception as e:
                    logger.error(f"获取下一个事件对话失败: {e}", exc_info=True)
                    raise
                
                # 输出详细信息到控制台
                self._print_dialogue_info(character_id, next_event, dialogue_data)
                
                # 获取合成图片URL（如果场景切换时已生成）
                composite_image_url = None
                if next_event.get('scene'):
                    try:
                        import os
                        import config
                        
                        # 查找最新的合成图片
                        scene_id = next_event.get('scene')
                        if os.path.isabs(config.COMPOSITE_IMAGE_SAVE_DIR):
                            composite_dir = config.COMPOSITE_IMAGE_SAVE_DIR
                        else:
                            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            composite_dir = os.path.join(backend_dir, config.COMPOSITE_IMAGE_SAVE_DIR)
                        
                        if os.path.exists(composite_dir):
                            # 查找该角色和场景的最新合成图片
                            import re
                            character_id_str = f"{character_id:04d}"
                            safe_scene_id = re.sub(r'[<>:"/\\|?*\s]', '_', scene_id)[:30]
                            pattern = re.compile(rf"^[^_]+_{re.escape(character_id_str)}_SCENE_{re.escape(safe_scene_id)}_composite_v\d+_\d{{8}}_\d{{6}}\.(jpg|jpeg|png)$", re.IGNORECASE)
                            
                            matching_files = []
                            for filename in os.listdir(composite_dir):
                                if pattern.match(filename):
                                    filepath = os.path.join(composite_dir, filename)
                                    matching_files.append((filename, os.path.getmtime(filepath)))
                            
                            if matching_files:
                                matching_files.sort(key=lambda x: x[1], reverse=True)
                                latest_filename = matching_files[0][0]
                                latest_filepath = os.path.join(composite_dir, latest_filename)
                                
                                # 验证并构建正确的URL
                                composite_image_url = self._validate_composite_image_url(latest_filepath)
                                if composite_image_url:
                                    logger.debug(f"找到合成图片: {latest_filepath} -> {composite_image_url}")
                                else:
                                    logger.warning(f"合成图片URL验证失败: {latest_filepath}")
                            else:
                                logger.debug(f"未找到匹配的合成图片: character_id={character_id}, scene_id={scene_id}")
                    except Exception as e:
                        logger.warning(f"获取合成图片URL失败: {e}", exc_info=True)
                
                # 更新状态值
                states = session.db_manager.get_character_states(character_id)
                if states:
                    current_states = {
                        'favorability': states.favorability,
                        'trust': states.trust,
                        'hostility': states.hostility,
                        'dependence': states.dependence,
                        'emotion': states.emotion,
                        'stress': states.stress,
                        'anxiety': states.anxiety,
                        'happiness': states.happiness,
                        'sadness': states.sadness,
                        'confidence': states.confidence,
                        'initiative': states.initiative,
                        'caution': states.caution
                    }
                else:
                    current_states = None
                
                # 获取场景图片URL（如果场景切换时已生成）
                scene_image_url = None
                next_scene = next_event.get('scene')
                if next_scene:
                    try:
                        import os
                        import config
                        from urllib.parse import quote
                        
                        # 查找最新的场景图片
                        scene_image_path = self.image_service.get_latest_scene_image_path(next_scene)
                        if scene_image_path and os.path.exists(scene_image_path):
                            # URL编码文件名，确保中文文件名能正确访问
                            encoded_filename = quote(os.path.basename(scene_image_path), safe='')
                            
                            # 判断图片来自哪个目录，使用对应的URL路径
                            if hasattr(config, 'SMALL_SCENE_IMAGE_SAVE_DIR'):
                                if os.path.isabs(config.SMALL_SCENE_IMAGE_SAVE_DIR):
                                    small_scene_dir = os.path.normpath(config.SMALL_SCENE_IMAGE_SAVE_DIR)
                                else:
                                    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                                    small_scene_dir = os.path.normpath(os.path.join(backend_dir, config.SMALL_SCENE_IMAGE_SAVE_DIR))
                                
                                # 标准化路径后进行比较，确保路径格式一致
                                normalized_scene_path = os.path.normpath(os.path.abspath(scene_image_path))
                                normalized_small_scene_dir = os.path.normpath(os.path.abspath(small_scene_dir))
                                
                                # 检查文件是否在smallscenes目录中
                                if os.path.exists(small_scene_dir) and normalized_scene_path.startswith(normalized_small_scene_dir):
                                    scene_image_url = f"/static/images/smallscenes/{encoded_filename}"
                                else:
                                    scene_image_url = f"/static/images/scenes/{encoded_filename}"
                            else:
                                scene_image_url = f"/static/images/scenes/{encoded_filename}"
                            logger.debug(f"找到场景图片: {scene_image_url} (路径: {scene_image_path})")
                    except Exception as e:
                        logger.warning(f"获取场景图片URL失败: {e}", exc_info=True)
                
                # 验证返回的composite_image_url（如果存在且不是None）
                validated_composite_url = None
                if composite_image_url:
                    # 如果composite_image_url是文件路径，需要验证并转换为URL
                    if composite_image_url.startswith('/') and not composite_image_url.startswith('/static/'):
                        validated_composite_url = self._validate_composite_image_url(composite_image_url)
                    elif composite_image_url.startswith('/static/images/composite/'):
                        # 已经是URL格式，验证文件是否存在
                        import os
                        import config
                        from urllib.parse import unquote
                        filename = unquote(os.path.basename(composite_image_url))
                        if os.path.isabs(config.COMPOSITE_IMAGE_SAVE_DIR):
                            composite_dir = config.COMPOSITE_IMAGE_SAVE_DIR
                        else:
                            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                            composite_dir = os.path.join(backend_dir, config.COMPOSITE_IMAGE_SAVE_DIR)
                        filepath = os.path.join(composite_dir, filename)
                        if os.path.exists(filepath):
                            validated_composite_url = composite_image_url
                            logger.debug(f"合成图片URL验证成功: {composite_image_url} -> {filepath}")
                        else:
                            logger.error(f"合成图片URL对应的文件不存在: {composite_image_url} -> {filepath}")
                            validated_composite_url = None
                    else:
                        validated_composite_url = composite_image_url
                
                response_data.update({
                    'character_dialogue': dialogue_data['character_dialogue'],
                    'player_options': dialogue_data['player_options'],
                    'story_background': next_event.get('story_background'),
                    'event_title': next_event.get('title'),
                    'scene': next_scene,
                    'scene_image_url': scene_image_url,  # 场景图片URL（用于前端显示）
                    'current_states': current_states,  # 更新状态值
                    'composite_image_url': validated_composite_url,  # 合成后的游戏场景图片（已验证）
                    'is_event_finished': True
                })
        
        return response_data
    
    def _print_dialogue_info(self, character_id: int, event: Dict, dialogue_data: Dict):
        """输出详细的对话信息到控制台"""
        try:
            # 获取角色信息
            character = self.character_service.db_manager.get_character(character_id)
            attributes = self.character_service.db_manager.get_character_attributes(character_id)
            states = self.character_service.db_manager.get_character_states(character_id)
            
            logger.debug("="*80)
            logger.debug("【游戏对话信息】")
            logger.debug("="*80)
            
            # 场景信息
            scene = event.get('scene', '未知场景')
            event_title = event.get('title', '未知事件')
            story_background = event.get('story_background', '')
            
            logger.debug(f"\n📍 【场景】: {scene}")
            logger.debug(f"📖 【事件】: {event_title}")
            if story_background:
                logger.debug(f"📝 【故事背景】: {story_background[:200]}{'...' if len(story_background) > 200 else ''}")
            
            # 角色设定
            if character:
                logger.debug(f"\n👤 【角色设定】")
                logger.debug(f"   姓名: {character.name}")
                logger.debug(f"   性别: {character.gender}")
                logger.debug(f"   外观: {character.appearance[:100]}{'...' if len(character.appearance) > 100 else ''}")
                logger.debug(f"   性格: {character.personality[:100]}{'...' if len(character.personality) > 100 else ''}")
                
                # 详细属性
                if attributes:
                    logger.debug(f"   详细属性:")
                    if hasattr(attributes, 'appearance_data') and attributes.appearance_data:
                        try:
                            app_data = json.loads(attributes.appearance_data) if isinstance(attributes.appearance_data, str) else attributes.appearance_data
                            if isinstance(app_data, dict):
                                if 'keywords' in app_data:
                                    logger.debug(f"      - 外观关键词: {', '.join(app_data['keywords']) if isinstance(app_data['keywords'], list) else app_data['keywords']}")
                                if 'height' in app_data:
                                    logger.debug(f"      - 身高: {app_data['height']}")
                                if 'weight' in app_data:
                                    logger.debug(f"      - 体重: {app_data['weight']}")
                        except:
                            pass
                    
                    if hasattr(attributes, 'personality_data') and attributes.personality_data:
                        try:
                            pers_data = json.loads(attributes.personality_data) if isinstance(attributes.personality_data, str) else attributes.personality_data
                            if isinstance(pers_data, dict) and 'keywords' in pers_data:
                                logger.debug(f"      - 性格关键词: {', '.join(pers_data['keywords']) if isinstance(pers_data['keywords'], list) else pers_data['keywords']}")
                        except:
                            pass
                    
                    if hasattr(attributes, 'age') and attributes.age:
                        logger.debug(f"      - 年龄: {attributes.age}")
            
            # 角色当前状态
            if states:
                logger.debug(f"\n💭 【角色当前状态】")
                logger.debug(f"   好感度: {states.favorability}/100")
                logger.debug(f"   信任度: {states.trust}/100")
                logger.debug(f"   敌意值: {states.hostility}/100")
                logger.debug(f"   依赖度: {states.dependence}/100")
                logger.debug(f"   情绪值: {states.emotion}/100")
                logger.debug(f"   压力值: {states.stress}/100")
                logger.debug(f"   焦虑值: {states.anxiety}/100")
                logger.debug(f"   快乐值: {states.happiness}/100")
                logger.debug(f"   悲伤值: {states.sadness}/100")
                logger.debug(f"   自信值: {states.confidence}/100")
                logger.debug(f"   主动性: {states.initiative}/100")
                logger.debug(f"   谨慎度: {states.caution}/100")
            
            # 对话内容
            character_dialogue = dialogue_data.get('character_dialogue', '')
            player_options = dialogue_data.get('player_options', [])
            
            logger.debug(f"\n💬 【角色对话】")
            logger.debug(f"   {character_dialogue}")
            
            if player_options:
                logger.debug(f"\n🎮 【玩家选项】")
                for idx, option in enumerate(player_options, 1):
                    option_text = option.get('text', '') if isinstance(option, dict) else str(option)
                    logger.debug(f"   {idx}. {option_text}")
            
            logger.debug("="*80)
            
        except Exception as e:
            logger.warning(f"输出对话信息时出错: {e}", exc_info=True)
    
    def check_ending(self, thread_id: str) -> Dict[str, Any]:
        """检查是否满足结局条件"""
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise ValueError(f"Thread {thread_id} not found")
        
        is_finished = session.story_engine.is_game_finished()
        
        if is_finished:
            # 获取角色状态值
            states = session.db_manager.get_character_states(session.character_id)
            if states:
                favorability = states.favorability
                trust = states.trust
                hostility = states.hostility
                
                # 确定结局类型
                if favorability > 60 and trust > 50:
                    ending_type = "good_ending"
                    ending_desc = "经过一系列事件，你们的关系变得更加亲密，这是一个美好的结局。"
                elif favorability < 30 or hostility > 50:
                    ending_type = "bad_ending"
                    ending_desc = "关系走向了不好的方向，你们之间的距离越来越远。"
                elif trust > 50 and favorability > 40:
                    ending_type = "neutral_ending"
                    ending_desc = "你们的关系保持在一个稳定的状态，未来还有无限可能。"
                else:
                    ending_type = "open_ending"
                    ending_desc = "故事还在继续，结局尚未确定..."
                
                return {
                    'has_ending': True,
                    'ending': {
                        'type': ending_type,
                        'description': ending_desc,
                        'favorability': favorability,
                        'trust': trust,
                        'hostility': hostility
                    }
                }
        
        return {
            'has_ending': False,
            'ending': None
        }
    
    def trigger_ending(self, thread_id: str) -> Dict[str, Any]:
        """触发结局"""
        session = self.session_manager.get_session(thread_id)
        if not session:
            raise ValueError(f"Thread {thread_id} not found")
        
        character_id = session.character_id
        
        # 获取结尾事件
        ending_event = session.story_engine.get_ending_event(character_id)
        
        # 获取第一轮对话
        dialogue_data = session.story_engine.get_next_dialogue_round(character_id)
        session.current_dialogue_round = dialogue_data
        session.story_engine.record_character_dialogue(dialogue_data['character_dialogue'])
        
        return {
            'event_title': ending_event.get('title', '结局'),
            'story_background': ending_event.get('story_background', ''),
            'scene': ending_event.get('scene'),
            'ending_type': ending_event.get('ending_type'),
            'character_dialogue': dialogue_data['character_dialogue'],
            'player_options': dialogue_data['player_options']
        }

