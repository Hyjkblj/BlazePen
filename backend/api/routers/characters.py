"""角色管理API路由"""
from fastapi import APIRouter, Depends
from typing import List
from api.schemas import (
    CreateCharacterRequest,
    CharacterResponse,
    CharacterImagesResponse,
    InitializeStoryRequest,
    RemoveBackgroundRequest
)
from api.response import success_response, error_response, not_found_response
from api.services.character_service import CharacterService
from api.dependencies import get_character_service, get_image_service, get_story_service_bundle
from api.services.image_service import ImageService
from api.story_route_handlers import handle_initialize_story_request
from api.story_schemas import StoryTurnApiResponse
from story.story_service_bundle import StoryServiceBundle
from utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/characters", tags=["角色管理"])


@router.post("/create", response_model=dict)
async def create_character(
    request: CreateCharacterRequest,
    character_service: CharacterService = Depends(get_character_service)
):
    """创建新角色"""
    try:
        import json
        logger.info("收到创建角色请求，开始处理...")
        # 转换请求数据
        if hasattr(request, "model_dump"):
            request_data = request.model_dump(exclude_none=True)
        else:
            request_data = request.dict(exclude_none=True)
        
        # 输出前端接收的人物设定数据到日志
        logger.debug("="*80)
        logger.debug("【前端接收的人物设定数据】")
        logger.debug("="*80)
        logger.debug(f"角色名称: {request_data.get('name', '未命名')}")
        logger.debug(f"性别: {request_data.get('gender', '未指定')}")
        logger.debug(f"年龄: {request_data.get('age', '未指定')}")
       
        
        # 外观设定
        appearance = request_data.get('appearance', {})
        logger.debug("外观设定:")
        if isinstance(appearance, dict):
            for key, value in appearance.items():
                if isinstance(value, (list, dict)):
                    logger.debug(f"  - {key}: {json.dumps(value, ensure_ascii=False, indent=4)}")
                else:
                    logger.debug(f"  - {key}: {value}")
        else:
            logger.debug(f"  {appearance}")
        
        # 性格设定
        personality = request_data.get('personality', {})
        logger.debug("性格设定:")
        if isinstance(personality, dict):
            for key, value in personality.items():
                if isinstance(value, (list, dict)):
                    logger.debug(f"  - {key}: {json.dumps(value, ensure_ascii=False, indent=4)}")
                else:
                    logger.debug(f"  - {key}: {value}")
        else:
            logger.debug(f"  {personality}")
        
        # 生成角色图片的prompt（包含组图指令）
        image_prompt = character_service.generate_character_image_prompt(
            request_data, 
            generate_group=True,  # 启用组图
            group_count=3  # 生成3张图片
        )
        logger.debug("【角色图片生成Prompt】")
        logger.debug("="*80)
        logger.debug(image_prompt)
        logger.debug("="*80)
        
        # 创建角色
        character_id = character_service.create_character(request_data)
        
        # 验证character_id是否有效
        if not character_id or character_id <= 0:
            logger.error(f"创建角色失败: 返回的character_id无效: {character_id}")
            return error_response(
                code=500,
                message=f"创建角色失败: 角色ID无效 ({character_id})"
            )
        
        logger.info(f"角色创建成功: character_id={character_id}")
        
        # 生成角色组图（如果服务已启用）
        # 获取user_id和image_type（用于文件命名）
        user_id = request_data.get('user_id')
        image_type = request_data.get('image_type', 'portrait')
        image_urls = None
        try:
            logger.info("开始调用生图服务（火山引擎 Seedream 组图 x3）...")
            image_urls = character_service.generate_character_image(
                request_data, character_id, user_id, image_type,
                generate_group=True, group_count=3  # 生成3张图片供前端三选一
            )
            if image_urls:
                logger.info(f"角色组图生成成功: 共 {len(image_urls)} 张图片")
                for i, url in enumerate(image_urls, 1):
                    logger.debug(f"图片 {i}: {url}")
            else:
                logger.warning("角色组图生成失败: image_urls为None或空")
        except Exception as e:
            logger.warning(f"角色图片生成失败: {e}", exc_info=True)
        
        # 获取角色信息
        character_info = character_service.get_character(character_id)
        
        # 确保character_id在响应中（即使get_character已经返回了）
        if 'character_id' not in character_info or not character_info.get('character_id'):
            character_info['character_id'] = str(character_id)
            logger.debug(f"补充character_id到响应: {character_id}")
        
        # 添加图片URL列表到响应（即使为空也要添加，确保前端能获取到）
        character_info['image_urls'] = image_urls if image_urls else []

        logger.info(f"创建角色响应: character_id={character_info.get('character_id')}, name={character_info.get('name')}, image_urls数量={len(character_info.get('image_urls', []))}")
        
        return success_response(data=character_info)
    except Exception as e:
        logger.error(f"创建角色失败: {e}", exc_info=True)
        return error_response(
            code=500,
            message=f"创建角色失败: {str(e)}",
            error={
                "type": type(e).__name__,
                "details": {
                    "message": str(e)
                }
            }
        )


@router.get("/scenes", response_model=dict)
async def get_scenes():
    """获取可用大场景列表（用于初遇场景选择）
    
    返回所有大场景（MAJOR_SCENES），并匹配对应的场景图片。
    图片文件名格式：{major_scene_id}_{场景名称}.{ext}，例如：school_学校.jpeg
    """
    try:
        import os
        import config
        
        # 导入场景数据
        try:
            from data.scenes import MAJOR_SCENES
            logger.info(f"成功导入场景数据，共 {len(MAJOR_SCENES)} 个大场景")
            logger.debug(f"大场景ID列表: {list(MAJOR_SCENES.keys())}")
        except Exception as import_error:
            logger.error(f"导入场景数据失败: {import_error}", exc_info=True)
            return error_response(code=500, message=f"导入场景数据失败: {str(import_error)}")
        
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if os.path.isabs(config.SCENE_IMAGE_SAVE_DIR):
            scene_images_dir = config.SCENE_IMAGE_SAVE_DIR
        else:
            scene_images_dir = os.path.join(backend_dir, config.SCENE_IMAGE_SAVE_DIR)
        
        # 获取所有场景图片文件，按大场景ID索引
        # 格式：{major_scene_id}_{场景名称}.{ext}，例如：school_学校.jpeg
        scene_images_by_id = {}  # 按major_scene_id索引
        
        if os.path.exists(scene_images_dir):
            image_extensions = ['.jpg', '.jpeg', '.png', '.webp']
            all_files = os.listdir(scene_images_dir)
            
            for filename in all_files:
                # 检查是否是图片文件
                filename_lower = filename.lower()
                if any(filename_lower.endswith(ext) for ext in image_extensions):
                    name_without_ext = os.path.splitext(filename)[0]
                    
                    # 尝试匹配格式：major_scene_id_场景名称
                    parts = name_without_ext.split('_', 1)
                    
                    if len(parts) == 2:
                        # 格式：{major_scene_id}_{场景名称}.{ext}
                        major_scene_id = parts[0]
                        scene_name_from_file = parts[1]
                        # URL编码文件名，确保中文文件名能正确访问
                        from urllib.parse import quote
                        encoded_filename = quote(filename, safe='')
                        scene_images_by_id[major_scene_id] = {
                            'filename': filename,
                            'url': f"/static/images/scenes/{encoded_filename}",
                            'name': scene_name_from_file
                        }
                        logger.debug(f"找到大场景图片: {major_scene_id} -> {filename}")
        else:
            logger.warning(f"场景图片目录不存在: {scene_images_dir}")
        
        # 构建大场景列表
        major_scenes_list = []
        
        for major_scene_id, major_scene_info in MAJOR_SCENES.items():
            scene_name = major_scene_info.get('name', major_scene_id)
            scene_description = major_scene_info.get('description', f'在{scene_name}中初次相遇')
            
            # 查找对应的图片
            image_url = None
            if major_scene_id in scene_images_by_id:
                image_url = scene_images_by_id[major_scene_id]['url']
            # 只在没有找到图片时输出警告（避免日志过多）
            # else:
            #     print(f"[警告] 大场景 {major_scene_id} 没有找到对应的图片文件")
            
            # 获取初遇事件列表（用于后端随机选择）
            opening_events = major_scene_info.get('opening_events', [])
            
            # 构建场景数据，确保 imageUrl 为字符串或 None（JSON序列化时 None 会变成 null）
            scene_data = {
                'id': major_scene_id,  # 大场景ID，用于传递给 initialize_story
                'name': scene_name,
                'description': scene_description,
                'imageUrl': image_url if image_url else None,  # 大场景图片URL，None 会被序列化为 null
                'openingEventsCount': len(opening_events)  # 该大场景下的初遇事件数量（前端显示用）
            }
            major_scenes_list.append(scene_data)
        
        logger.info(f"总共返回 {len(major_scenes_list)} 个大场景")
        logger.debug("场景列表详情:")
        for scene in major_scenes_list:
            logger.debug(f"  - {scene['id']}: {scene['name']} (图片: {scene.get('imageUrl', '无')})")
        
        if len(major_scenes_list) == 0:
            logger.warning("场景列表为空！")
            logger.warning(f"MAJOR_SCENES 数量: {len(MAJOR_SCENES)}")
        
        return success_response(data={'scenes': major_scenes_list})
    except Exception as e:
        logger.error(f"获取场景列表失败: {e}", exc_info=True)
        return error_response(code=500, message=f"获取场景列表失败: {str(e)}")


@router.get("/scenes/{major_scene_id}/opening-events", response_model=dict)
async def get_opening_events(major_scene_id: str):
    """获取指定大场景下的所有初遇事件列表（用于用户选择）
    
    Args:
        major_scene_id: 大场景ID（如 'school', 'company' 等）
    
    Returns:
        该大场景下的所有初遇事件列表
    """
    try:
        from data.scenes import MAJOR_SCENES
        
        # 获取大场景信息
        major_scene = MAJOR_SCENES.get(major_scene_id)
        if not major_scene:
            return error_response(code=404, message=f"大场景 {major_scene_id} 不存在")
        
        # 获取初遇事件列表
        opening_events = major_scene.get('opening_events', [])
        
        if not opening_events:
            return error_response(code=404, message=f"大场景 {major_scene_id} 没有初遇事件")
        
        # 格式化返回数据
        events_list = []
        for event in opening_events:
            events_list.append({
                'id': event.get('id'),
                'title': event.get('title'),
                'description': event.get('description'),
                'sub_scene': event.get('sub_scene'),  # 对应的小场景ID
            })
        
        logger.info(f"返回大场景 {major_scene_id} 的 {len(events_list)} 个初遇事件")
        return success_response(data={
            'major_scene_id': major_scene_id,
            'major_scene_name': major_scene.get('name', major_scene_id),
            'events': events_list
        })
    except Exception as e:
        logger.error(f"获取初遇事件列表失败: {e}", exc_info=True)
        return error_response(code=500, message=f"获取初遇事件列表失败: {str(e)}")


@router.get("/{character_id}", response_model=dict)
async def get_character(
    character_id: str,
    character_service: CharacterService = Depends(get_character_service)
):
    """获取角色信息"""
    try:
        character_id_int = int(character_id)
        character_info = character_service.get_character(character_id_int)
        return success_response(data=character_info)
    except ValueError:
        return error_response(code=400, message="无效的角色ID")
    except Exception as e:
        if "不存在" in str(e):
            return not_found_response(message="角色不存在")
        return error_response(code=500, message=f"获取角色失败: {str(e)}")


@router.get("/{character_id}/images", response_model=dict)
async def get_character_images(
    character_id: str,
    character_service: CharacterService = Depends(get_character_service)
):
    """获取角色图片列表"""
    try:
        # 检查character_id是否有效
        if not character_id or character_id == 'undefined' or character_id == 'null':
            return error_response(code=400, message="无效的角色ID: character_id不能为空或undefined")
        
        character_id_int = int(character_id)
        if character_id_int <= 0:
            return error_response(code=400, message="无效的角色ID: 角色ID必须大于0")
        
        images = character_service.get_character_images(character_id_int)
        return success_response(data={"images": images})
    except ValueError:
        return error_response(code=400, message=f"无效的角色ID: '{character_id}' 不是有效的数字")
    except Exception as e:
        logger.error(f"获取角色图片失败: {e}", exc_info=True)
        return error_response(code=500, message=f"获取角色图片失败: {str(e)}")


@router.post("/{character_id}/remove-background", response_model=dict)
async def remove_character_background(
    character_id: str,
    request: RemoveBackgroundRequest = RemoveBackgroundRequest(),
    character_service: CharacterService = Depends(get_character_service),
    image_service: ImageService = Depends(get_image_service)
):
    """选择角色图片并处理透明背景
    
    流程：
    1. 处理选中图片的透明背景
    2. 删除未选中的图片
    3. 返回透明背景图片URL
    
    Args:
        character_id: 角色ID
        request: 请求体，包含image_url（可选）、image_urls（所有图片URL列表）、selected_index（选中的索引）
    """
    try:
        # 解析请求体
        image_url = request.image_url if request else None
        image_urls = request.image_urls if request else None
        selected_index = request.selected_index if request else None
        
        character_id_int = int(character_id)
        
        # 如果没有提供image_url，获取角色最新图片
        if not image_url:
            images = character_service.get_character_images(character_id_int)
            if not images or len(images) == 0:
                return error_response(code=404, message="角色没有图片")
            # 使用最新图片（第一张）
            image_url = images[0]
        
        logger.info(f"用户选择角色图片: {image_url}")
        
        # 先处理透明背景（使用基于原文件名的命名逻辑）
        logger.info("开始处理透明背景...")
        transparent_path = image_service.remove_background_with_rembg(
            image_path=image_url,
            character_id=character_id_int,
            rename_to_standard=False  # 使用基于原文件名的命名逻辑
        )
        
        if not transparent_path:
            return error_response(code=500, message="背景去除失败")
        
        # 构建返回的URL（静态文件路径）
        import os
        from urllib.parse import quote
        filename = os.path.basename(transparent_path)
        result_url = f"/static/images/characters/{quote(filename, safe='')}"
        
        logger.info(f"透明背景处理成功: {result_url}")
        
        # 等待透明背景处理完成后，再删除未选中的图片
        deleted_count = 0
        if image_urls and selected_index is not None and len(image_urls) > 1:
            deleted_count = image_service.delete_unselected_character_images(
                character_id=character_id_int,
                image_urls=image_urls,
                selected_index=selected_index
            )
            logger.info(f"已删除 {deleted_count} 张未选中的图片")
        
        # 返回透明背景图片URL
        logger.info(f"返回透明背景图片URL: {result_url}")
        return success_response(data={
            "selected_image_url": image_url,  # 原始图片URL
            "transparent_url": result_url,    # 透明背景图片URL
            "local_path": transparent_path,
            "deleted_count": deleted_count
        })
        
    except ValueError:
        return error_response(code=400, message="无效的角色ID")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"选择图片失败: {str(e)}", exc_info=True)
        return error_response(code=500, message=f"选择图片失败: {str(e)}", error={"traceback": error_trace})


@router.post("/initialize-story", response_model=StoryTurnApiResponse)
async def initialize_story(
    request: InitializeStoryRequest,
    story_service_bundle: StoryServiceBundle = Depends(get_story_service_bundle),
):
    """初始化故事（触发初遇场景）"""

    return await handle_initialize_story_request(
        request=request,
        story_service_bundle=story_service_bundle,
        route_name="story.initialize.legacy",
    )

